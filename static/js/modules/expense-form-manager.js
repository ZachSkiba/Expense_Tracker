// Expense Form Management Module
class ExpenseFormManager {
    constructor(options = {}) {
        this.formSelector = options.formSelector || '#expense-form';
        this.urls = options.urls || {};
        
        this.form = document.querySelector(this.formSelector);
        if (!this.form) {
            console.warn('Expense form not found');
            return;
        }
        
        this.categorySelect = document.getElementById('category-select');
        this.userSelect = document.getElementById('user-select');
        this.descContainer = document.getElementById('category-desc-container');
        this.descInput = document.getElementById('category-description');
        this.amountInput = document.querySelector('input[name="amount"]');
        
        this.init();
    }
    
    init() {
        this.setupCategoryHandling();
        this.setupUserHandling();
        this.setupParticipantHandling();
        this.setupFormValidation();
        this.setupAutoComplete();
        
        // Initialize form state
        this.updateCategoryDescriptionVisibility();
        this.updateSplitPreview();
    }
    
    setupCategoryHandling() {
        if (!this.categorySelect) return;
        
        this.categorySelect.addEventListener('change', (e) => {
            if (e.target.value === 'manage') {
                this.redirectToManage('categories');
                return;
            }
            this.updateCategoryDescriptionVisibility();
        });
    }
    
    setupUserHandling() {
        if (!this.userSelect) return;
        
        this.userSelect.addEventListener('change', (e) => {
            if (e.target.value === 'manage') {
                this.redirectToManage('users');
                return;
            }
            this.autoSelectPayerAsParticipant(e.target.value);
        });
    }
    
    setupParticipantHandling() {
        const participantCheckboxes = document.querySelectorAll('input[name="participant_ids"]');
        participantCheckboxes.forEach(checkbox => {
            checkbox.addEventListener('change', () => this.updateSplitPreview());
        });
        
        // Also update when amount changes
        if (this.amountInput) {
            this.amountInput.addEventListener('input', () => this.updateSplitPreview());
        }
    }
    
    setupFormValidation() {
        this.form.addEventListener('submit', (e) => {
            // Check for manage selections
            if (this.categorySelect && this.categorySelect.value === 'manage') {
                e.preventDefault();
                return false;
            }
            
            if (this.userSelect && this.userSelect.value === 'manage') {
                e.preventDefault();
                return false;
            }
            
            // Check participants
            const participantCheckboxes = document.querySelectorAll('input[name="participant_ids"]:checked');
            if (participantCheckboxes.length === 0) {
                e.preventDefault();
                alert('Please select at least one participant for this expense.');
                return false;
            }
        });
    }
    
    setupAutoComplete() {
        if (this.descInput && window.createAutocomplete) {
            window.createAutocomplete(this.descInput, 'suggestions-container');
        }
    }
    
    updateCategoryDescriptionVisibility() {
        if (!this.categorySelect || !this.descContainer) return;
        
        if (this.categorySelect.value && this.categorySelect.value !== 'manage') {
            this.descContainer.style.display = 'block';
        } else {
            this.descContainer.style.display = 'none';
        }
    }
    
    autoSelectPayerAsParticipant(payerId) {
        if (!payerId) return;
        
        const payerCheckbox = document.getElementById(`participant-${payerId}`);
        if (payerCheckbox && !payerCheckbox.checked) {
            payerCheckbox.checked = true;
            this.updateSplitPreview();
        }
    }
    
    updateSplitPreview() {
        const participantCheckboxes = document.querySelectorAll('input[name="participant_ids"]:checked');
        const splitPreview = document.getElementById('split-preview');
        const splitDetails = document.getElementById('split-details');
        
        if (!splitPreview || !splitDetails) return;
        
        const amount = parseFloat(this.amountInput?.value) || 0;
        const participantCount = participantCheckboxes.length;
        
        if (amount > 0 && participantCount > 0) {
            const sharePerPerson = amount / participantCount;
            
            let detailsHtml = `<div>Total: $${amount.toFixed(2)} ÷ ${participantCount} people = $${sharePerPerson.toFixed(2)} per person</div>`;
            detailsHtml += '<div style="margin-top: 8px; font-size: 0.85em;">Participants: ';
            
            const participantNames = [];
            participantCheckboxes.forEach(checkbox => {
                const label = document.querySelector(`label[for="${checkbox.id}"]`);
                if (label) {
                    participantNames.push(label.textContent);
                }
            });
            
            detailsHtml += participantNames.join(', ') + '</div>';
            
            splitDetails.innerHTML = detailsHtml;
            splitPreview.style.display = 'block';
        } else {
            splitPreview.style.display = 'none';
        }
    }
    
    redirectToManage(type) {
        // Remove required attributes to prevent validation
        document.querySelectorAll('input[required], select[required]').forEach(el => {
            el.removeAttribute('required');
        });
        
        const nextUrl = encodeURIComponent(window.location.href);
        const dest = type === 'categories' ? this.urls.manageCategories : this.urls.manageUsers;
        window.location.href = `${dest}?next=${nextUrl}`;
    }
}

// Export for use
window.ExpenseFormManager = ExpenseFormManager;