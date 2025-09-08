/**
 * Recurring Payments Manager - FIXED VERSION
 * Handles all recurring payment functionality
 */

class RecurringPaymentsManager {
    constructor() {
        this.form = document.getElementById('recurring-payment-form');
        this.tableBody = document.getElementById('recurring-payments-table-body');
        this.isEditing = false;
        this.editingId = null;
        this.isSubmitting = false; // Prevent double submission
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadRecurringPayments();
    }
    
    bindEvents() {
        // Form submission
        if (this.form) {
            this.form.addEventListener('submit', (e) => this.handleFormSubmit(e));
        }
        
        // Frequency change handler
        const frequencySelect = this.form.querySelector('[name="frequency"]');
        if (frequencySelect) {
            frequencySelect.addEventListener('change', (e) => this.handleFrequencyChange(e));
        }
    }
    
    async handleFormSubmit(event) {
        event.preventDefault();
        
        // Prevent double submission
        if (this.isSubmitting) {
            console.log('Already submitting, ignoring duplicate submission');
            return;
        }
        
        const formData = new FormData(this.form);
        const data = this.parseFormData(formData);
        
        // Validate form
        if (!this.validateForm(data)) {
            return;
        }
        
        try {
            this.isSubmitting = true;
            this.setLoadingState(true);
            
            let response;
            if (this.isEditing && this.editingId) {
                response = await this.updateRecurringPayment(this.editingId, data);
            } else {
                response = await this.createRecurringPayment(data);
            }
            
            if (response.success) {
                this.showSuccessMessage(
                    this.isEditing ? 'Recurring payment updated successfully!' : 'Recurring payment created successfully!'
                );
                this.resetForm();
                
                // Immediately reload the table to show the new/updated payment
                await this.loadRecurringPayments();
                
                // Also refresh the main expenses table if it exists
                if (window.expenseTableManager) {
                    window.expenseTableManager.loadExpenses();
                }
            } else {
                this.showErrorMessage(response.message || 'An error occurred');
            }
        } catch (error) {
            console.error('Error submitting recurring payment:', error);
            this.showErrorMessage('An error occurred while saving the recurring payment');
        } finally {
            this.isSubmitting = false;
            this.setLoadingState(false);
        }
    }
    
    parseFormData(formData) {
        const data = {};
        
        // Basic fields
        data.amount = formData.get('amount');
        data.category_id = formData.get('category_id');
        data.category_description = formData.get('category_description');
        data.user_id = formData.get('user_id');
        data.frequency = formData.get('frequency');
        data.interval_value = formData.get('interval_value');
        data.start_date = formData.get('start_date');
        data.next_due_date = formData.get('next_due_date'); // Add this for editing
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
            this.showErrorMessage(errors.join('<br>'));
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
        
        return await response.json();
    }
    
    async updateRecurringPayment(id, data) {
        const response = await fetch(`${window.urls.recurringPaymentsApi}/${id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });
        
        return await response.json();
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
            const isDueOrOverdue = dueDateClass === 'due-today' || nextDueDate < today;
            
            return `
                <tr>
                    <td>
                        <strong>${this.escapeHtml(payment.category_name)}</strong>
                        ${payment.category_description ? `<br><small>${this.escapeHtml(payment.category_description)}</small>` : ''}
                    </td>
                    <td>$${parseFloat(payment.amount).toFixed(2)}</td>
                    <td>${this.escapeHtml(payment.user_name)}</td>
                    <td>
                        <span class="frequency-display">
                            ${this.formatFrequency(payment.frequency, payment.interval_value)}
                        </span>
                    </td>
                    <td>${this.formatDate(payment.start_date)}</td>
                    <td>${payment.end_date ? this.formatDate(payment.end_date) : 'Never'}</td>
                    <td>
                        <span class="due-date ${dueDateClass}">
                            ${this.formatDate(payment.next_due_date)}
                        </span>
                    </td>
                    <td>
                        <span class="status-badge ${payment.is_active ? 'status-active' : 'status-inactive'}">
                            ${payment.is_active ? 'Active' : 'Inactive'}
                        </span>
                    </td>
                    <td>
                        <div class="participants-display">
                            ${payment.participants && payment.participants.length > 0 ? payment.participants.join(', ') : 'All users'}
                        </div>
                    </td>
                    <td>
                        <button class="action-btn edit-btn" onclick="recurringPaymentsManager.editRecurringPayment(${payment.id})">
                            Edit
                        </button>
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
    
    async editRecurringPayment(id) {
        try {
            // Find the recurring payment data
            const response = await fetch(`${window.urls.recurringPaymentsApi}/${id}`);
            const data = await response.json();
            
            if (data.success) {
                this.populateFormForEdit(data.recurring_payment, id);
            } else {
                this.showErrorMessage('Error loading recurring payment for editing');
            }
        } catch (error) {
            console.error('Error loading recurring payment:', error);
            this.showErrorMessage('Error loading recurring payment for editing');
        }
    }
    
    populateFormForEdit(payment, id) {
        this.isEditing = true;
        this.editingId = id;
        
        // Update form title
        const title = document.getElementById('recurring-form-title');
        if (title) title.textContent = 'Edit Recurring Payment';
        
        // Update submit button
        const submitBtn = document.getElementById('recurring-submit-btn');
        if (submitBtn) submitBtn.textContent = 'Update Recurring Payment';
        
        // Show next due date field
        const nextDueGroup = document.getElementById('next-due-group');
        if (nextDueGroup) nextDueGroup.style.display = 'block';
        
        // Populate form fields
        this.form.querySelector('[name="amount"]').value = payment.amount;
        this.form.querySelector('[name="category_id"]').value = payment.category_id;
        this.form.querySelector('[name="category_description"]').value = payment.category_description || '';
        this.form.querySelector('[name="user_id"]').value = payment.user_id;
        this.form.querySelector('[name="frequency"]').value = payment.frequency;
        this.form.querySelector('[name="interval_value"]').value = payment.interval_value;
        this.form.querySelector('[name="start_date"]').value = payment.start_date;
        this.form.querySelector('[name="next_due_date"]').value = payment.next_due_date;
        this.form.querySelector('[name="end_date"]').value = payment.end_date || '';
        this.form.querySelector('[name="is_active"]').value = payment.is_active.toString();
        
        // Handle frequency change to show interval field
        this.handleFrequencyChange({ target: this.form.querySelector('[name="frequency"]') });
        
        // Set participants
        const participantIds = payment.participant_ids || [];
        this.form.querySelectorAll('[name="participant_ids"]').forEach(checkbox => {
            checkbox.checked = participantIds.includes(parseInt(checkbox.value));
        });
        
        // Scroll to form
        document.getElementById('recurring-form-title').scrollIntoView({ behavior: 'smooth' });
    }
    
    resetForm() {
        this.isEditing = false;
        this.editingId = null;
        this.form.reset();
        
        // Reset form title and button
        const title = document.getElementById('recurring-form-title');
        if (title) title.textContent = 'Add New Recurring Payment';
        
        const submitBtn = document.getElementById('recurring-submit-btn');
        if (submitBtn) submitBtn.textContent = 'Add Recurring Payment';
        
        // Hide interval group and next due group
        const intervalGroup = document.getElementById('interval-group');
        if (intervalGroup) intervalGroup.style.display = 'none';
        
        const nextDueGroup = document.getElementById('next-due-group');
        if (nextDueGroup) nextDueGroup.style.display = 'none';
        
        // Clear all checkboxes
        this.form.querySelectorAll('[name="participant_ids"]').forEach(checkbox => {
            checkbox.checked = false;
        });
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
                
                // Force refresh the main expenses table
                if (window.expenseTableManager && window.expenseTableManager.loadExpenses) {
                    await window.expenseTableManager.loadExpenses();
                }
                
                // Trigger any other refresh functions
                if (window.refreshAllData) {
                    window.refreshAllData();
                }
            } else {
                this.showErrorMessage(result.message || 'Error processing payment');
            }
        } catch (error) {
            console.error('Error processing payment:', error);
            this.showErrorMessage('Error processing payment');
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
        const date = new Date(dateString);
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
        if (this.submitButton) {
            if (loading) {
                this.submitButton.disabled = true;
                this.submitButton.style.pointerEvents = 'none';
                this.submitButton.innerHTML = '<span class="spinner"></span> Saving...';
            } else {
                this.submitButton.disabled = false;
                this.submitButton.style.pointerEvents = '';
                this.submitButton.innerHTML = this.isEditing ? 'Update Recurring Payment' : 'Add Recurring Payment';
            }
        }
    }
    
    showSuccessMessage(message) {
        // Simple alert for now - you can customize this
        alert(message);
        console.log('SUCCESS:', message);
    }
    
    showErrorMessage(message) {
        // Simple alert for now - you can customize this
        alert('Error: ' + message);
        console.error('ERROR:', message);
    }
}

// Global functions for template onclick handlers
function openRecurringPaymentsModal() {
    const modal = document.getElementById('recurringPaymentsModal');
    if (modal) {
        modal.style.display = 'block';
        
        // Load recurring payments when modal opens
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

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.recurringPaymentsManager = new RecurringPaymentsManager();
});