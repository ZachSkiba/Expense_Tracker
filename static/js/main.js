console.log('main.js loaded');
// Main JavaScript initialization - UPDATED with income support
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
    const expenseTable = document.querySelector('.expenses-table');
    const hasExpenseData = document.getElementById('categories-data') || document.getElementById('users-data');
    
    if (expenseTable && hasExpenseData) {
        window.expenseTableManager = new window.ExpenseTableManager({
            tableSelector: '.expenses-table',
            errorSelector: '#table-error',
            urls: urls
        });
        
        // Initialize expense filter integration
        if (window.ExpenseFilterIntegration) {
            window.expenseFilterIntegration = new window.ExpenseFilterIntegration({
                urls: urls
            });
        }
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

     // Initialize recurring payments manager
    if (typeof RecurringPaymentsManager !== 'undefined') {
        window.recurringPaymentsManager = new RecurringPaymentsManager();
        console.log('Recurring payments manager initialized');
    }

    // Initialize income allocation manager for personal trackers
    if (window.isPersonalTracker === 'true') {
        // Initialize income manager first
        if (typeof IncomeManager !== 'undefined' && !window.incomeManager) {
            window.incomeManager = new IncomeManager();
            console.log('Income manager initialized');
        }
        
        // Initialize income allocation manager
        if (typeof IncomeAllocationManager !== 'undefined') {
            setTimeout(() => {
                if (!window.incomeAllocationManager) {
                    window.incomeAllocationManager = new IncomeAllocationManager();
                    console.log('Income allocation manager initialized');
                }
            }, 300);
        }
    }
        
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

// UPDATED: Group-aware data loading function
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
            
            // Initialize expense filter integration for recent expenses table
            if (window.ExpenseFilterIntegration && !window.expenseFilterIntegration) {
                window.expenseFilterIntegration = new window.ExpenseFilterIntegration({
                    urls: window.urls
                });
            }
        }
        
        // Update expense count display
        updateExpenseCount();
        
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

// UPDATED: Group-aware balance data loading
async function loadBalancesData() {
    try {
        // Get group ID from global variable if available
        const groupId = window.groupId;
        
        // Build API URLs with group context if available
        const balancesUrl = groupId ? `/api/balances/${groupId}` : '/api/balances';
        const suggestionsUrl = groupId ? `/api/settlement-suggestions/${groupId}` : '/api/settlement-suggestions';
        
        console.log('[DEBUG] Loading balances data for group:', groupId || 'all');
        
        const [balancesResponse, suggestionsResponse] = await Promise.all([
            fetch(balancesUrl),
            fetch(suggestionsUrl)
        ]);
        
        if (!balancesResponse.ok || !suggestionsResponse.ok) {
            throw new Error('API responses not OK');
        }
        
        const balancesData = await balancesResponse.json();
        const suggestionsData = await suggestionsResponse.json();
    
        updateBalancesDisplay(balancesData.balances);
        updateSettlementSuggestionsDisplay(suggestionsData.suggestions);
        updateHeaderStatus(balancesData.balances);
        
        console.log('[DEBUG] Group-specific data loaded successfully');
        
    } catch (error) {
        console.error('[ERROR] Error loading group data:', error);
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

    // Use consistent styling that matches the original format
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

// Update expense count display
function updateExpenseCount() {
    const expenseRows = document.querySelectorAll('table tbody tr[data-expense-id]');
    const countElement = document.getElementById('expenses-count');
    if (countElement) {
        const count = expenseRows.length;
        countElement.textContent = count === 1 ? '1 expense' : `${count} expenses`;
        countElement.style.display = count > 0 ? 'block' : 'none';
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
        return `${parseFloat(amount).toFixed(2)}`;
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

function openRecurringPaymentsModal() {
    const modal = document.getElementById('recurringPaymentsModal');
    if (modal) {
        modal.style.display = 'block';
        
        // Load recurring payments data if manager exists
        if (window.recurringPaymentsManager) {
            window.recurringPaymentsManager.loadRecurringPayments();
        }
    }
}

// REPLACE the entire openIncomeModal function:
function openIncomeModal() {
    console.log('=== openIncomeModal called ===');
    const modal = document.getElementById('incomeModal');
    console.log('Modal element:', modal);
    
    if (!modal) {
        console.error('Income modal not found in DOM!');
        return;
    }
    
    console.log('Current modal display style:', modal.style.display);
    modal.style.display = 'block';
    console.log('After setting display to block:', modal.style.display);

    // Force show with additional styles
    modal.style.visibility = 'visible';
    modal.style.opacity = '1';

    // Load income data if managers are already initialized
    if (window.incomeManager) {
        setTimeout(() => {
            window.incomeManager.loadIncomeCategories().then(() => {
                window.incomeManager.loadIncomeEntries();
            });
        }, 100);
    }
}


// NEW: Income form reset function
function resetIncomeForm() {
    if (window.incomeManager) {
        window.incomeManager.resetForm();
    }
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

// Close modals when clicking outside
window.onclick = function(event) {
    // Only close modals if clicking directly on the modal backdrop, not on buttons or content
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        if (event.target === modal) {
            console.log('Closing modal:', modal.id);
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

// UPDATED: Global settlement refresh function that settlement manager can call
window.globalRefreshBalances = async function() {
    try {
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

// Prevent multiple form submissions
function preventMultipleSubmissions(formId, buttonId) {
    const form = document.getElementById(formId);
    if (!form) return;

    form.addEventListener("submit", () => {
        const submitBtn = document.getElementById(buttonId);
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerText = "Processing..."; // Optional UX improvement
        }
    });
}

document.addEventListener("DOMContentLoaded", () => {
    preventMultipleSubmissions("expense-form", "add-expense-btn");
    preventMultipleSubmissions("settlement-form", "record-payment-btn");
    preventMultipleSubmissions("recurring-form", "recurring-submit-btn");
    
    // Add income form prevention
    if (window.isPersonalTracker === 'true') {
        preventMultipleSubmissions("income-form", "income-submit-btn");
    }
});

// Make functions globally available
window.openIncomeModal = openIncomeModal;
window.resetIncomeForm = resetIncomeForm;
window.openRecurringPaymentsModal = openRecurringPaymentsModal;