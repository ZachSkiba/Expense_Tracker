// Main JavaScript initialization
document.addEventListener('DOMContentLoaded', function() {
    // Get page context from body data attribute or URL
    const pageName = document.body.dataset.page || getPageFromURL();
    
    // URLs configuration (populated from templates)
    const urls = window.urls || {};
    
    // Initialize modules based on current page and available elements
    initializeForPage(pageName, urls);
});

function getPageFromURL() {
    const path = window.location.pathname;
    if (path.includes('add-expense')) return 'add-expense';
    if (path.includes('expenses')) return 'expenses';
    if (path.includes('balances')) return 'balances';
    if (path.includes('users')) return 'users';
    if (path.includes('categories')) return 'categories';
    return 'unknown';
}

function initializeForPage(pageName, urls) {
    // Initialize expense table if it exists
    const expenseTable = document.querySelector('table');
    const hasExpenseData = document.getElementById('categories-data') || document.getElementById('users-data');
    
    if (expenseTable && hasExpenseData) {
        new window.ExpenseTableManager({
            tableSelector: 'table',
            errorSelector: '#table-error',
            urls: urls
        });
    }
    
    // Initialize expense form if it exists
    const expenseForm = document.getElementById('expense-form');
    if (expenseForm) {
        new window.ExpenseFormManager({
            formSelector: '#expense-form',
            urls: urls
        });
    }
    
    // Initialize autocomplete for any description fields (fallback)
    const descriptionInputs = document.querySelectorAll('input[name*="description"], input[id*="description"]');
    descriptionInputs.forEach(input => {
        if (window.createAutocomplete && !input.dataset.autocompleteInitialized) {
            window.createAutocomplete(input);
            input.dataset.autocompleteInitialized = 'true';
        }
    });
    
    // Page-specific initializations
    switch (pageName) {
        case 'add-expense':
            console.log('Add expense page initialized');
            break;
        case 'expenses':
            console.log('Expenses page initialized');
            break;
        case 'balances':
            console.log('Balances page initialized');
            break;
        default:
            console.log(`Page '${pageName}' initialized with basic functionality`);
    }
}

// Global utility functions
window.AppUtils = {
    showMessage: function(message, color = 'black', duration = 5000) {
        // Try to find a message container
        let messageContainer = document.querySelector('#table-error, .message-container, .alert-container');
        
        if (!messageContainer) {
            // Create temporary message container
            messageContainer = document.createElement('div');
            messageContainer.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background: white;
                border: 1px solid #ddd;
                padding: 15px;
                border-radius: 5px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                z-index: 10000;
                max-width: 300px;
            `;
            document.body.appendChild(messageContainer);
        }
        
        messageContainer.style.color = color;
        messageContainer.innerHTML = message;
        
        if (duration > 0) {
            setTimeout(() => {
                if (messageContainer.parentNode === document.body) {
                    document.body.removeChild(messageContainer);
                } else {
                    messageContainer.innerHTML = '';
                }
            }, duration);
        }
    },
    
    formatCurrency: function(amount) {
        return `$${parseFloat(amount).toFixed(2)}`;
    },
    
    validatePositiveNumber: function(value, fieldName = 'Value') {
        const num = parseFloat(value);
        if (isNaN(num) || num <= 0) {
            throw new Error(`${fieldName} must be a positive number`);
        }
        return num;
    }
};