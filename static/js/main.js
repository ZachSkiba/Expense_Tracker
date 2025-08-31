// Main JavaScript initialization - UPDATED VERSION (Consistent styling fixes)
document.addEventListener('DOMContentLoaded', function() {
    // Get page context from body data attribute or URL
    const pageName = document.body.dataset.page || getPageFromURL();
    
    // URLs configuration (populated from templates)
    const urls = window.urls || {};
    
    // Initialize modules based on current page and available elements
    initializeForPage(pageName, urls);
    
    // Load data ONCE after everything is initialized
    loadInitialData();
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

// SINGLE data loading function called once after initialization
async function loadInitialData() {
    try {
        // Only load balances data if we have the required containers
        const balancesContainer = document.getElementById('balances-container');
        const settlementsContainer = document.getElementById('settlements-container');
        
        if (balancesContainer || settlementsContainer) {
            await loadBalancesData();
        }
        
        // Initialize autocomplete for description input
        const descInput = document.getElementById('category-description');
        if (descInput && window.createAutocomplete && !descInput.dataset.autocompleteInitialized) {
            window.createAutocomplete(descInput, 'suggestions-container');
            descInput.dataset.autocompleteInitialized = 'true';
        }
        
        // Initialize expense table manager if expenses exist and not already initialized
        const expenseTable = document.querySelector('.recent-expenses table');
        if (expenseTable && window.ExpenseTableManager && !window.expenseTableManager) {
            window.expenseTableManager = new window.ExpenseTableManager({
                tableSelector: '.recent-expenses table',
                errorSelector: '.recent-expenses #table-error',
                urls: window.urls
            });
        }
        
        // Initialize expense form manager if not already initialized
        if (window.ExpenseFormManager && !window.expenseFormManager) {
            const expenseForm = document.getElementById('expense-form');
            if (expenseForm) {
                window.expenseFormManager = new window.ExpenseFormManager({
                    formSelector: '#expense-form',
                    urls: window.urls
                });
            }
        }
        
    } catch (error) {
        console.error('[ERROR] Failed to load initial data:', error);
    }
}

// Load balances data from API - SINGLE CALL VERSION
async function loadBalancesData() {
    try {
        
        const [balancesResponse, suggestionsResponse] = await Promise.all([
            fetch('/api/balances'),
            fetch('/api/settlement-suggestions')
        ]);
        
        if (!balancesResponse.ok || !suggestionsResponse.ok) {
            throw new Error('API responses not OK');
        }
        
        const balancesData = await balancesResponse.json();
        const suggestionsData = await suggestionsResponse.json();
    
        
        updateBalancesDisplay(balancesData.balances);
        updateSettlementSuggestionsDisplay(suggestionsData.suggestions);
        updateHeaderStatus(balancesData.balances);
        
    } catch (error) {
        console.error('[ERROR] Error loading data:', error);
        const container = document.getElementById('balances-container');
        if (container) {
            container.innerHTML = 
                '<div style="text-align: center; padding: 20px; color: #e74c3c;">Error loading balances</div>';
        }
    }
}

function updateBalancesDisplay(balances) {
    const container = document.getElementById('balances-container');
    if (!container) return;
    
    if (!balances || balances.length === 0) {
        container.innerHTML = '<div style="text-align: center; padding: 20px; color: #7f8c8d;">No users found</div>';
        return;
    }

    const balanceItems = balances.map(balance => {
        const initial = balance.user_name.charAt(0).toUpperCase();
        const status = balance.balance > 0.01 ? 'positive' : balance.balance < -0.01 ? 'negative' : 'even';
        const statusText = balance.balance > 0.01 ? 'owed' : balance.balance < -0.01 ? 'owes' : 'even';
        const amount = Math.abs(balance.balance);

        return `
            <div class="balance-item ${status}">
                <div class="user-info">
                    <div class="user-avatar">${initial}</div>
                    <div>
                        <div class="user-name">${balance.user_name}</div>
                    </div>
                </div>
                <div class="balance-amount">
                    <div class="amount">$${amount.toFixed(2)}</div>
                    <div class="status">${statusText}</div>
                </div>
            </div>
        `;
    }).join('');

    container.innerHTML = balanceItems;
}

function updateSettlementSuggestionsDisplay(suggestions) {
    const container = document.getElementById('settlements-container');
    if (!container) return;
    
    if (!suggestions || suggestions.length === 0) {
        container.innerHTML = '<div class="no-settlements">🎉 All settled! No payments needed.</div>';
        return;
    }

    // **FIXED**: Use consistent styling that matches the original format
    const suggestionItems = suggestions.map(suggestion => `
        <div class="settlement-item">
            <strong>${suggestion.from}</strong> should pay <strong>${suggestion.to}</strong> 
            <span class="settlement-amount">$${suggestion.amount.toFixed(2)}</span>
        </div>
    `).join('');

    container.innerHTML = suggestionItems;
}

function updateHeaderStatus(balances) {
    const statusIndicator = document.querySelector('.status-indicator');
    if (!statusIndicator) return;

    const hasImbalances = balances.some(b => Math.abs(b.balance) > 0.01);
    
    if (hasImbalances) {
        statusIndicator.textContent = 'Pending Settlements';
        statusIndicator.className = 'status-indicator pending';
        statusIndicator.style.background = '#fff3cd';
        statusIndicator.style.color = '#856404';
    } else {
        statusIndicator.textContent = 'All Even';
        statusIndicator.className = 'status-indicator all-even';
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
    },
    
    // Function to manually refresh balances if needed
    refreshBalances: async function() {
        await loadBalancesData();
    }
};

function openAddExpenseModal() {
    document.getElementById('addExpenseModal').style.display = 'block';
}

function openSettleUpModal() {
    document.getElementById('settleUpModal').style.display = 'block';
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

// Close modals when clicking outside
window.onclick = function(event) {
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });
}

// Category handling
function handleCategoryChange(select) {
    const descContainer = document.getElementById('category-desc-container');

    if (select.value === 'manage') {
        window.location.href = window.urls.manageCategories + '?next=' + encodeURIComponent(window.location.href);
        return;
    }
    
    if (select.value && select.value !== 'manage') {
        descContainer.style.display = 'block';
    } else {
        descContainer.style.display = 'none';
    }
}

// User handling
function handleUserChange(select) {
    if (select.value === 'manage') {
        window.location.href = window.urls.manageUsers + '?next=' + encodeURIComponent(window.location.href);
        return;
    }
    
    // Auto-select payer as participant
    const payerCheckbox = document.getElementById(`participant-${select.value}`);
    if (payerCheckbox && !payerCheckbox.checked) {
        payerCheckbox.checked = true;
        updateSplitPreview();
    }
}

// Participant handling
function toggleAllParticipants() {
    const checkboxes = document.querySelectorAll('input[name="participant_ids"]');
    const anyUnchecked = Array.from(checkboxes).some(cb => !cb.checked);
    
    checkboxes.forEach(checkbox => {
        checkbox.checked = anyUnchecked;
    });
    
    updateSplitPreview();
}

function updateSplitPreview() {
    const participantCheckboxes = document.querySelectorAll('input[name="participant_ids"]:checked');
    const splitPreview = document.getElementById('split-preview');
    const splitDetails = document.getElementById('split-details');
    const amountInput = document.querySelector('input[name="amount"]');
    
    if (!splitPreview || !splitDetails) return;
    
    const amount = parseFloat(amountInput?.value) || 0;
    const participantCount = participantCheckboxes.length;
    
    if (amount > 0 && participantCount > 0) {
        const sharePerPerson = amount / participantCount;
        
        let detailsHtml = `<div>Total: ${amount.toFixed(2)} ÷ ${participantCount} people = ${sharePerPerson.toFixed(2)} per person</div>`;
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

// **UPDATED**: Global settlement refresh function that settlement manager can call
window.globalRefreshBalances = async function() {
    try {
        console.log('[DEBUG] Global balance refresh triggered...');
        
        // Use the same load function that main.js uses initially
        await loadBalancesData();
        
        // If balance manager exists, also refresh it
        if (window.balanceManager && typeof window.balanceManager.refresh === 'function') {
            await window.balanceManager.refresh();
        }
        
        console.log('[DEBUG] Global balance refresh completed');
    } catch (error) {
        console.error('[ERROR] Global balance refresh failed:', error);
    }
};