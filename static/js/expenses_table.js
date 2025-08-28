// Initialize expenses table functionality

// Wait for DOM to be ready
document.addEventListener("DOMContentLoaded", function() {
    // Initialize table functionality
    
    const tableError = document.getElementById('table-error');
    
    // Get data from script tags
    let categoriesData = [];
    let usersData = [];
    
    try {
        const categoriesScript = document.getElementById('categories-data');
        const usersScript = document.getElementById('users-data');
        
        if (categoriesScript) {
            categoriesData = JSON.parse(categoriesScript.textContent);
        }
        if (usersScript) {
            usersData = JSON.parse(usersScript.textContent);
        }
        
        // Categories and users data loaded successfully
    } catch (e) {
        console.error("Error parsing data:", e);
    }
    
    function showMessage(message, color = 'black') {
        if (tableError) {
            tableError.style.color = color;
            tableError.innerHTML = message;
            setTimeout(() => {
                tableError.innerHTML = '';
            }, 8000);
        }
    }

    // DELETE FUNCTIONALITY
    function setupDeleteButtons() {
        const deleteButtons = document.querySelectorAll('.delete-btn');
        
        deleteButtons.forEach((btn, index) => {
            
            // Remove any existing event listeners by cloning the button
            const newBtn = btn.cloneNode(true);
            btn.parentNode.replaceChild(newBtn, btn);
            
            newBtn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                const row = this.closest('tr');
                const expenseId = this.getAttribute('data-expense-id') || row.getAttribute('data-expense-id');
                
                if (!expenseId) {
                    showMessage('Error: No expense ID found', 'red');
                    return;
                }
                
                if (!confirm("Are you sure you want to delete this expense?")) {
                    return;
                }
                
                // Disable button during request
                this.disabled = true;
                this.textContent = "Deleting...";
                
                fetch(`/delete_expense/${expenseId}`, { 
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(result => {
                    if (result.success) {
                        row.remove();
                        showMessage('Expense deleted successfully!', 'green');
                    } else {
                        showMessage(result.error || 'Error deleting expense', 'red');
                        // Re-enable button
                        this.disabled = false;
                        this.textContent = "❌ Delete";
                    }
                })
                .catch(error => {
                    showMessage('Network error deleting expense: ' + error.message, 'red');
                    // Re-enable button
                    this.disabled = false;
                    this.textContent = "❌ Delete";
                });
            });
        });
    }

    // EDIT FUNCTIONALITY
    function setupEditableCells() {
        const editableCells = document.querySelectorAll('td.editable');
        
        editableCells.forEach((cell, index) => {
            
            cell.style.cursor = 'pointer';
            cell.style.backgroundColor = '#f9f9f9';
            cell.title = 'Click to edit';
            
            // Remove any existing event listeners by cloning
            const newCell = cell.cloneNode(true);
            cell.parentNode.replaceChild(newCell, cell);
            
            newCell.addEventListener('click', function(e) {
                e.stopPropagation();
                
                // Check if already editing
                if (this.querySelector('input, select')) {
                    return;
                }
                
                const classes = Array.from(this.classList);
                const type = classes.find(c => c !== 'editable'); // amount, category, description, user, date
                const currentValue = this.getAttribute('data-value') || '';
                const originalHTML = this.innerHTML;
                
                // Create input based on type
                let input;
                if (type === 'amount') {
                    input = document.createElement('input');
                    input.type = 'number';
                    input.step = '0.01';
                    input.min = '0.01';
                    input.value = parseFloat(currentValue || '0').toFixed(2);
                } else if (type === 'description') {
                    input = document.createElement('input');
                    input.type = 'text';
                    input.value = currentValue;
                    input.autocomplete = 'off';
                    
                    // Store autocomplete creation for after input is added to DOM
                    let autocomplete = null;
                    
                    // Prepare cleanup function
                    const cleanupAutocomplete = () => {
                        if (autocomplete && typeof autocomplete.cleanup === 'function') {
                            autocomplete.cleanup();
                        }
                    };
                    
                    // Store cleanup function for later use
                    window.descriptionCleanup = cleanupAutocomplete;
                } else if (type === 'date') {
                    input = document.createElement('input');
                    input.type = 'date';
                    input.value = currentValue;
                } else if (type === 'category') {
                    input = document.createElement('select');
                    // placeholder
                    const placeholder = document.createElement('option');
                    placeholder.value = '';
                    placeholder.textContent = 'Select category';
                    placeholder.disabled = true;
                    placeholder.selected = true;
                    input.appendChild(placeholder);
                    // options
                    categoriesData.forEach(cat => {
                        const option = document.createElement('option');
                        option.value = cat.name;
                        option.textContent = cat.name;
                        option.selected = cat.name === currentValue;
                        input.appendChild(option);
                    });
                    // manage
                    const manageOpt = document.createElement('option');
                    manageOpt.value = 'manage';
                    manageOpt.textContent = '➕ Add/Remove Categories';
                    input.appendChild(manageOpt);
                } else if (type === 'user') {
                    input = document.createElement('select');
                    // placeholder
                    const placeholder = document.createElement('option');
                    placeholder.value = '';
                    placeholder.textContent = 'Select user';
                    placeholder.disabled = true;
                    placeholder.selected = true;
                    input.appendChild(placeholder);
                    // options
                    usersData.forEach(user => {
                        const option = document.createElement('option');
                        option.value = user.name;
                        option.textContent = user.name;
                        option.selected = user.name === currentValue;
                        input.appendChild(option);
                    });
                    // manage
                    const manageOpt = document.createElement('option');
                    manageOpt.value = 'manage';
                    manageOpt.textContent = '➕ Add/Remove Users';
                    input.appendChild(manageOpt);
                } else {
                    // Fallback for any other type
                    input = document.createElement('input');
                    input.type = 'text';
                    input.value = currentValue;
                }
                
                // Style the input
                input.style.width = '100%';
                input.style.border = '2px solid blue';
                input.style.padding = '4px';
                input.style.boxSizing = 'border-box';
                
                // Replace content with input
                this.innerHTML = '';
                this.appendChild(input);
                input.focus();
                
                // Set up autocomplete after input is in the DOM (for description fields)
                if (type === 'description') {
                    // Small delay to ensure DOM is fully updated, then set up autocomplete
                    setTimeout(() => {
                        if (typeof window.createAutocomplete === 'function') {
                            autocomplete = window.createAutocomplete(input);
                        }
                    }, 10);
                }
                
                const saveEdit = () => {
                    // Clean up autocomplete if editing description
                    if (type === 'description' && window.descriptionCleanup) {
                        window.descriptionCleanup();
                        window.descriptionCleanup = null;
                    }
                    
                    const newValue = input.value.trim();
                    const row = this.closest('tr');
                    const expenseId = row.getAttribute('data-expense-id');
                    
                    // Basic validation
                    if (type === 'amount') {
                        const numValue = parseFloat(newValue);
                        if (isNaN(numValue) || numValue <= 0) {
                            showMessage('Amount must be a positive number', 'red');
                            this.innerHTML = originalHTML;
                            return;
                        }
                    }
                    
                    if (!newValue && type !== 'description') {
                        showMessage(`${type} cannot be empty`, 'red');
                        this.innerHTML = originalHTML;
                        return;
                    }
                    
                    // Prepare data - map field names to what the server expects
                    const data = {};
                    if (type === 'amount') {
                        data.amount = parseFloat(newValue);
                    } else if (type === 'category') {
                        data.category = newValue;
                    } else if (type === 'description') {
                        data.description = newValue;
                    } else if (type === 'user') {
                        data.user = newValue;
                    } else if (type === 'date') {
                        data.date = newValue;
                    }
                    
                    // Show loading state
                    input.disabled = true;
                    input.style.backgroundColor = '#f0f0f0';
                    
                    // Send to server
                    fetch(`/edit_expense/${expenseId}`, {
                        method: 'POST',
                        headers: { 
                            'Content-Type': 'application/json',
                            'X-Requested-With': 'XMLHttpRequest'
                        },
                        body: JSON.stringify(data)
                    })
                    .then(response => {
                        if (!response.ok) {
                            throw new Error(`HTTP error! status: ${response.status}`);
                        }
                        return response.json();
                    })
                    .then(result => {
                        if (result.success) {
                            // Update display
                            if (type === 'amount') {
                                const numValue = parseFloat(newValue);
                                this.innerHTML = `$${numValue.toFixed(2)}`;
                                this.setAttribute('data-value', numValue.toFixed(2));
                            } else {
                                this.innerHTML = newValue || '';
                                this.setAttribute('data-value', newValue);
                            }
                            showMessage('Updated successfully!', 'green');
                        } else {
                            showMessage(result.error || 'Update failed', 'red');
                            this.innerHTML = originalHTML;
                        }
                    })
                    .catch(error => {
                        showMessage('Network error: ' + error.message, 'red');
                        this.innerHTML = originalHTML;
                    });
                };
                
                const cancelEdit = () => {
                    // Clean up autocomplete if editing description
                    if (type === 'description' && window.descriptionCleanup) {
                        window.descriptionCleanup();
                        window.descriptionCleanup = null;
                    }
                    
                    this.innerHTML = originalHTML;
                };
                
                // Event listeners
                input.addEventListener('blur', function(e) {
                    // Small delay to allow click events on buttons to fire first
                    setTimeout(saveEdit, 100);
                });
                
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
                    input.addEventListener('change', function() {
                        if (this.value === 'manage') {
                            const nextUrl = encodeURIComponent(window.location.href);
                            const dest = type === 'category' ? urls.manageCategories : urls.manageUsers;
                            window.location.href = `${dest}?next=${nextUrl}`;
                            return;
                        }
                        // For normal selection, immediately save
                        saveEdit();
                    });
                }
            });
        });
    }
    
    // Initialize everything
    setupDeleteButtons();
    setupEditableCells();
});