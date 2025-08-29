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

        // Make URLs available to JavaScript modules
    

        // Load existing JavaScript functionality
        document.addEventListener('DOMContentLoaded', function() {
            // Load balances and settlements data
            loadBalancesData();
            
            // Initialize autocomplete
            const descInput = document.getElementById('category-description');
            if (descInput && window.createAutocomplete) {
                window.createAutocomplete(descInput, 'suggestions-container');
            }
            
            // Initialize expense table manager if expenses exist
            const expenseTable = document.querySelector('table');
            if (expenseTable && window.ExpenseTableManager) {
                new window.ExpenseTableManager({
                    tableSelector: 'table',
                    errorSelector: '#table-error',
                    urls: window.urls
                });
            }
            
            // Initialize expense form manager
            if (window.ExpenseFormManager) {
                new window.ExpenseFormManager({
                    formSelector: '#expense-form',
                    urls: window.urls
                });
            }
        });

        // Load balances data from API
        async function loadBalancesData() {
            try {
                const [balancesResponse, settlementsResponse] = await Promise.all([
                    fetch('/api/balances'),
                    fetch('/api/settlements')
                ]);
                
                const balancesData = await balancesResponse.json();
                const settlementsData = await settlementsResponse.json();
                
                updateBalancesDisplay(balancesData.balances);
                updateSettlementsDisplay(settlementsData.settlements);
                updateHeaderStatus(balancesData.balances);
                
            } catch (error) {
                console.error('Error loading data:', error);
                document.getElementById('balances-container').innerHTML = 
                    '<div style="text-align: center; padding: 20px; color: #e74c3c;">Error loading balances</div>';
            }
        }

        function updateBalancesDisplay(balances) {
            const container = document.getElementById('balances-container');
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

        function updateSettlementsDisplay(settlements) {
            const container = document.getElementById('settlements-container');
            
            if (!settlements || settlements.length === 0) {
                container.innerHTML = '<div class="no-settlements">🎉 All settled! No payments needed.</div>';
                return;
            }

            const settlementItems = settlements.map(settlement => `
                <div class="settlement-item">
                    <strong>${settlement.from}</strong> should pay <strong>${settlement.to}</strong> 
                    <span class="settlement-amount">$${settlement.amount.toFixed(2)}</span>
                </div>
            `).join('');

            container.innerHTML = settlementItems;
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