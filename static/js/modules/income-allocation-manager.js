/**
 * Income Allocation Manager - Handles income allocation functionality
 */

class IncomeAllocationManager {
    constructor() {
        this.allocationCategories = [];
        this.currentIncomeEntry = null;
        this.allocationIndex = 0;
        
        this.init();
    }
    
    init() {
        this.loadAllocationCategories();
        this.bindEvents();
        this.setupMainFormAllocation();
    }
    
    bindEvents() {
        // Main income form allocation events
        const enableAllocationCheckbox = document.getElementById('enable-allocation');
        if (enableAllocationCheckbox) {
            enableAllocationCheckbox.addEventListener('change', (e) => {
                this.toggleAllocationSection(e.target.checked);
            });
        }
        
        // Amount input change to update summary
        const amountInput = document.querySelector('#income-form input[name="amount"]');
        if (amountInput) {
            amountInput.addEventListener('input', () => {
                this.updateAllocationSummary();
            });
        }
        
        // Modal allocation form
        const allocationForm = document.getElementById('allocation-form');
        if (allocationForm) {
            allocationForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.saveAllocations();
            });
        }
    }
    
    async loadAllocationCategories() {
        try {
            const groupId = window.groupId;
            const response = await fetch(`/api/income/allocation/categories/${groupId}`);
            const data = await response.json();
            
            if (data.success) {
                this.allocationCategories = data.allocation_categories;
                this.populateAllocationSelects();
                console.log('[ALLOCATION] Loaded', this.allocationCategories.length, 'allocation categories');
            } else {
                console.error('[ALLOCATION] Error loading allocation categories:', data.message);
            }
        } catch (error) {
            console.error('[ALLOCATION] Error loading allocation categories:', error);
        }
    }
    
    populateAllocationSelects() {
        // Populate all allocation category selects
        const selects = document.querySelectorAll('select[name="allocation_category_id[]"], select[name="allocation_category_id"]');
        
        selects.forEach(select => {
            // Clear existing options except placeholder
            while (select.children.length > 1) {
                select.removeChild(select.lastChild);
            }
            
            // Add allocation categories
            this.allocationCategories.forEach(category => {
                const option = document.createElement('option');
                option.value = category.id;
                option.textContent = category.name;
                select.appendChild(option);
            });
        });
    }
    
    setupMainFormAllocation() {
        // Set up the main income form allocation section
        const allocationEntries = document.getElementById('allocation-entries');
        if (allocationEntries) {
            // Add event listeners to existing allocation inputs
            this.bindAllocationEntryEvents(allocationEntries.querySelector('.allocation-entry'));
        }
    }
    
    toggleAllocationSection(enabled) {
        const allocationEntries = document.getElementById('allocation-entries');
        if (allocationEntries) {
            if (enabled) {
                allocationEntries.classList.add('show');
            } else {
                allocationEntries.classList.remove('show');
            }
            this.updateAllocationSummary();
        }
    }
    
    addAllocation() {
        const container = document.getElementById('allocation-entries');
        const addButton = container.querySelector('.add-allocation-btn');
        
        this.allocationIndex++;
        
        const newEntry = document.createElement('div');
        newEntry.className = 'allocation-entry';
        newEntry.setAttribute('data-allocation-index', this.allocationIndex);
        
        newEntry.innerHTML = `
            <select name="allocation_category_id[]" required>
                <option value="" disabled selected>Select allocation category</option>
            </select>
            <input type="number" step="0.01" min="0.01" name="allocation_amount[]" placeholder="Amount" required>
            <input type="text" name="allocation_notes[]" placeholder="Notes (optional)">
            <button type="button" class="remove-allocation" onclick="window.incomeAllocationManager.removeAllocation(this)">Remove</button>
        `;
        
        // Insert before the add button
        container.insertBefore(newEntry, addButton);
        
        // Populate the new select WITH the placeholder properly selected
        const select = newEntry.querySelector('select');
        this.allocationCategories.forEach(category => {
            const option = document.createElement('option');
            option.value = category.id;
            option.textContent = category.name;
            select.appendChild(option);
        });
        
        // Explicitly set the select to show placeholder
        select.value = '';
        
        // Bind events to the new entry
        this.bindAllocationEntryEvents(newEntry);
    }
    
    removeAllocation(button) {
        const entry = button.closest('.allocation-entry');
        const container = entry.parentNode;
        
        // Don't remove if it's the only entry
        const entries = container.querySelectorAll('.allocation-entry');
        if (entries.length > 1) {
            entry.remove();
            this.updateAllocationSummary();
        } else {
            // Just clear the values instead of removing
            entry.querySelector('select').value = '';
            entry.querySelector('input[type="number"]').value = '';
            entry.querySelector('input[type="text"]').value = '';
            this.updateAllocationSummary();
        }
    }
    
    bindAllocationEntryEvents(entry) {
        if (!entry) return;
        
        const amountInput = entry.querySelector('input[type="number"]');
        if (amountInput) {
            amountInput.addEventListener('input', () => {
                this.updateAllocationSummary();
            });
        }
    }
    
    updateAllocationSummary() {
        const enabledCheckbox = document.getElementById('enable-allocation');
        if (!enabledCheckbox || !enabledCheckbox.checked) {
            return;
        }
        
        const amountInput = document.querySelector('#income-form input[name="amount"]');
        const incomeAmount = parseFloat(amountInput?.value) || 0;
        
        const allocationAmountInputs = document.querySelectorAll('#allocation-entries input[name="allocation_amount[]"]');
        let totalAllocated = 0;
        
        allocationAmountInputs.forEach(input => {
            const amount = parseFloat(input.value) || 0;
            totalAllocated += amount;
        });
        
        const remaining = incomeAmount - totalAllocated;
        
        // Update display
        document.getElementById('income-amount-display').textContent = `$${incomeAmount.toFixed(2)}`;
        document.getElementById('total-allocated-display').textContent = `$${totalAllocated.toFixed(2)}`;
        
        const remainingDisplay = document.getElementById('remaining-display');
        const remainingSpan = remainingDisplay.querySelector('span:last-child');
        remainingSpan.textContent = `$${remaining.toFixed(2)}`;
        
        // Color coding
        remainingDisplay.classList.remove('positive', 'negative');
        if (remaining > 0) {
            remainingDisplay.classList.add('positive');
        } else if (remaining < 0) {
            remainingDisplay.classList.add('negative');
        }
    }
    
    async viewAllocations(incomeEntryId) {
    try {
        const groupId = window.groupId;
        console.log('[ALLOCATION] Loading allocations for income entry:', incomeEntryId, 'in group:', groupId);
        const response = await fetch(`/api/income/allocation/entries/${groupId}/${incomeEntryId}`);
        const data = await response.json();
        
        console.log('[ALLOCATION] API Response:', data);
        
        if (data.success) {
            this.currentIncomeEntry = data.income_entry;
            console.log('[ALLOCATION] Current income entry set:', this.currentIncomeEntry);
            console.log('[ALLOCATION] Allocations:', data.allocations);
            this.showAllocationDetailsModal(data.income_entry, data.allocations);
        } else {
            this.showMessage('Error loading allocations: ' + data.message, 'red');
        }
    } catch (error) {
        console.error('[ALLOCATION] Error loading allocations:', error);
        this.showMessage('Error loading allocations', 'red');
    }
}
    
        showAllocationDetailsModal(incomeEntry, allocations) {
            // Populate income entry details
            const detailsContainer = document.getElementById('allocation-income-details');
            detailsContainer.innerHTML = `
                <h4>Income Entry Details</h4>
                <div class="income-detail-row">
                    <span><strong>Amount:</strong></span>
                    <span>$${parseFloat(incomeEntry.amount).toFixed(2)}</span>
                </div>
                <div class="income-detail-row">
                    <span><strong>Category:</strong></span>
                    <span>${incomeEntry.income_category_name || incomeEntry.category_name || 'N/A'}</span>
                </div>
                <div class="income-detail-row">
                    <span><strong>Description:</strong></span>
                    <span>${incomeEntry.description || 'No description'}</span>
                </div>
                <div class="income-detail-row">
                    <span><strong>Received By:</strong></span>
                    <span>${incomeEntry.user_name || 'N/A'}</span>
                </div>
                <div class="income-detail-row">
                    <span><strong>Date:</strong></span>
                    <span>${this.formatDate(incomeEntry.date)}</span>
                </div>
            `;
        
        // Populate allocation form
        this.populateAllocationForm(allocations);
        
        // Show modal
        document.getElementById('allocationDetailsModal').style.display = 'block';
    }
    
    populateAllocationForm(allocations) {
    const container = document.getElementById('modal-allocation-entries');
    
    // Clear everything including any existing buttons
    container.innerHTML = '';
    
    console.log('[ALLOCATION] Populating form with', allocations.length, 'allocations');
    
    if (allocations.length === 0) {
        // Add one empty row
        this.addAllocationRow();
    } else {
        // Add existing allocations
        allocations.forEach((allocation, index) => {
            console.log('[ALLOCATION] Adding row for allocation', index, allocation);
            this.addAllocationRow(allocation);
        });
    }
    
    // Add the "Add Allocation" button (only one)
    const addButton = document.createElement('button');
    addButton.type = 'button';
    addButton.className = 'add-allocation-btn';
    addButton.textContent = '+ Add Allocation';
    addButton.onclick = (e) => {
        e.preventDefault();
        this.addAllocationRow();
    };
    container.appendChild(addButton);
    
    this.updateModalAllocationSummary();
}
    
    addAllocationRow(allocation = null) {
    const container = document.getElementById('modal-allocation-entries');
    if (!container) {
        console.error('[ALLOCATION] Container not found!');
        return;
    }
    
    const addButton = container.querySelector('.add-allocation-btn');
    
    const newEntry = document.createElement('div');
    newEntry.className = 'allocation-entry';
    
    newEntry.innerHTML = `
        <select name="allocation_category_id" required>
            <option value="" disabled selected>Select allocation category</option>
        </select>
        <input type="number" step="0.01" min="0.01" name="allocation_amount" placeholder="Amount" required 
               value="${allocation ? allocation.amount : ''}" 
               oninput="window.incomeAllocationManager.updateModalAllocationSummary()"
               onchange="window.incomeAllocationManager.updateModalAllocationSummary()">
        <input type="text" name="allocation_notes" placeholder="Notes (optional)" 
               value="${allocation ? (allocation.notes || '') : ''}">
        <button type="button" class="remove-allocation" onclick="window.incomeAllocationManager.removeModalAllocation(this)">Remove</button>
    `;
    
    // Insert before the add button or append to container
    if (addButton) {
        container.insertBefore(newEntry, addButton);
    } else {
        container.appendChild(newEntry);
    }
    
    // Populate select options
    const select = newEntry.querySelector('select');
    this.allocationCategories.forEach(category => {
        const option = document.createElement('option');
        option.value = category.id;
        option.textContent = category.name;
        option.selected = allocation && allocation.allocation_category_id === category.id;
        select.appendChild(option);
    });
    
    console.log('[ALLOCATION] Added allocation row, total rows now:', container.querySelectorAll('.allocation-entry').length);
    console.log('[ALLOCATION] Container HTML:', container.innerHTML.substring(0, 200));
}
    
    removeModalAllocation(button) {
        const entry = button.closest('.allocation-entry');
        const container = entry.parentNode;
        
        // Don't remove if it's the only entry
        const entries = container.querySelectorAll('.allocation-entry');
        if (entries.length > 1) {
            entry.remove();
        } else {
            // Just clear the values
            entry.querySelector('select').value = '';
            entry.querySelector('input[name="allocation_amount"]').value = '';
            entry.querySelector('input[name="allocation_notes"]').value = '';
        }
        
        this.updateModalAllocationSummary();
    }
    
    updateModalAllocationSummary() {
        if (!this.currentIncomeEntry) return;
        
        const incomeAmount = parseFloat(this.currentIncomeEntry.amount);
        const amountInputs = document.querySelectorAll('#modal-allocation-entries input[name="allocation_amount"]');
        
        let totalAllocated = 0;
        amountInputs.forEach(input => {
            const amount = parseFloat(input.value) || 0;
            totalAllocated += amount;
        });
        
        const remaining = incomeAmount - totalAllocated;
        
        const summaryContainer = document.getElementById('modal-allocation-summary');
        summaryContainer.innerHTML = `
            <div class="allocation-summary-row">
                <span>Income Amount:</span>
                <span>$${incomeAmount.toFixed(2)}</span>
            </div>
            <div class="allocation-summary-row">
                <span>Total Allocated:</span>
                <span>$${totalAllocated.toFixed(2)}</span>
            </div>
            <div class="allocation-summary-row ${remaining > 0 ? 'positive' : remaining < 0 ? 'negative' : ''}">
                <span>Remaining:</span>
                <span>$${remaining.toFixed(2)}</span>
            </div>
        `;
    }

    bindModalEvents() {
    // Bind the add allocation button in modal
    const addButton = document.querySelector('#modal-allocation-entries .add-allocation-btn');
    if (addButton) {
        // Remove any existing onclick handler
        addButton.onclick = null;
        // Add new handler
        addButton.onclick = (e) => {
            e.preventDefault();
            this.addAllocationRow();
        };
        console.log('[ALLOCATION] Bound add allocation button in modal');
    }
}
    
    async saveAllocations() {
        if (!this.currentIncomeEntry) return;
        
        const form = document.getElementById('allocation-form');
        const entries = form.querySelectorAll('.allocation-entry');
        
        const allocations = [];
        
        for (let entry of entries) {
            const categoryId = entry.querySelector('select[name="allocation_category_id"]').value;
            const amount = entry.querySelector('input[name="allocation_amount"]').value;
            const notes = entry.querySelector('input[name="allocation_notes"]').value;
            
            if (categoryId && amount && parseFloat(amount) > 0) {
                allocations.push({
                    allocation_category_id: parseInt(categoryId),
                    amount: parseFloat(amount),
                    notes: notes.trim() || null
                });
            }
        }
        
        if (allocations.length === 0) {
            this.showMessage('Please add at least one allocation', 'red');
            return;
        }
        
        try {
            const groupId = window.groupId;
            const response = await fetch(`/api/income/allocation/entries/${groupId}/${this.currentIncomeEntry.id}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ allocations })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showMessage('Allocations saved successfully!', 'green');
                document.getElementById('allocationDetailsModal').style.display = 'none';
                
                // Refresh income entries table if income manager exists
                if (window.incomeManager) {
                    window.incomeManager.loadIncomeEntries();
                }
            } else {
                this.showMessage('Error saving allocations: ' + result.message, 'red');
            }
        } catch (error) {
            console.error('[ALLOCATION] Error saving allocations:', error);
            this.showMessage('Error saving allocations', 'red');
        }
    }
    
    // Utility methods
    formatDate(dateString) {
        if (!dateString) return '';
        const [year, month, day] = dateString.split('-').map(Number);
        const date = new Date(year, month - 1, day);
        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric'
        });
    }
    
    showMessage(message, color = 'black') {
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
window.addAllocation = function() {
    if (window.incomeAllocationManager) {
        window.incomeAllocationManager.addAllocation();
    }
};

window.removeAllocation = function(button) {
    if (window.incomeAllocationManager) {
        window.incomeAllocationManager.removeAllocation(button);
    }
};

// Make class globally available
window.IncomeAllocationManager = IncomeAllocationManager;