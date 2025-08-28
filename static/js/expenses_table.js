console.log("expenses_table.js loaded");

// Wait for DOM to be ready
document.addEventListener("DOMContentLoaded", function() {
    console.log("DOM ready, initializing table functionality");
    
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
        
        console.log("Categories data:", categoriesData);
        console.log("Users data:", usersData);
    } catch (e) {
        console.error("Error parsing data:", e);
    }
    
    function showMessage(message, color = 'black') {
        console.log("Showing message:", message, color);
        if (tableError) {
            tableError.style.color = color;
            tableError.innerHTML = message;
            setTimeout(() => {
                tableError.innerHTML = '';
            }, 5000);
        }
    }

    // DELETE FUNCTIONALITY
    function setupDeleteButtons() {
        console.log("Setting up delete buttons");
        const deleteButtons = document.querySelectorAll('.delete-btn');
        console.log("Found", deleteButtons.length, "delete buttons");
        
        deleteButtons.forEach((btn, index) => {
            console.log(`Setting up delete button ${index}`);
            
            // Remove any existing event listeners by cloning the button
            const newBtn = btn.cloneNode(true);
            btn.parentNode.replaceChild(newBtn, btn);
            
            newBtn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                console.log("Delete button clicked!");
                
                const row = this.closest('tr');
                const expenseId = this.getAttribute('data-expense-id') || row.getAttribute('data-expense-id');
                
                console.log("Expense ID to delete:", expenseId);
                
                if (!expenseId) {
                    console.error("No expense ID found");
                    showMessage('Error: No expense ID found', 'red');
                    return;
                }
                
                if (!confirm("Are you sure you want to delete this expense?")) {
                    return;
                }
                
                console.log("Attempting to delete expense", expenseId);
                
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
                    console.log("Delete response status:", response.status);
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(result => {
                    console.log("Delete result:", result);
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
                    console.error('Delete fetch error:', error);
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
        console.log("Setting up editable cells");
        const editableCells = document.querySelectorAll('td.editable');
        console.log("Found", editableCells.length, "editable cells");
        
        editableCells.forEach((cell, index) => {
            console.log(`Setting up editable cell ${index}`);
            
            cell.style.cursor = 'pointer';
            cell.style.backgroundColor = '#f9f9f9';
            cell.title = 'Click to edit';
            
            // Remove any existing event listeners by cloning
            const newCell = cell.cloneNode(true);
            cell.parentNode.replaceChild(newCell, cell);
            
            newCell.addEventListener('click', function(e) {
                e.stopPropagation();
                console.log("Editable cell clicked!");
                
                // Check if already editing
                if (this.querySelector('input, select')) {
                    console.log("Already editing, ignoring");
                    return;
                }
                
                const classes = Array.from(this.classList);
                const type = classes.find(c => c !== 'editable'); // amount, category, description, user, date
                const currentValue = this.getAttribute('data-value') || '';
                const originalHTML = this.innerHTML;
                
                console.log("Starting edit - type:", type, "value:", currentValue);
                
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
                } else if (type === 'date') {
                    input = document.createElement('input');
                    input.type = 'date';
                    input.value = currentValue;
                } else if (type === 'category') {
                    input = document.createElement('select');
                    categoriesData.forEach(cat => {
                        const option = document.createElement('option');
                        option.value = cat.name;
                        option.textContent = cat.name;
                        option.selected = cat.name === currentValue;
                        input.appendChild(option);
                    });
                } else if (type === 'user') {
                    input = document.createElement('select');
                    usersData.forEach(user => {
                        const option = document.createElement('option');
                        option.value = user.name;
                        option.textContent = user.name;
                        option.selected = user.name === currentValue;
                        input.appendChild(option);
                    });
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
                
                const saveEdit = () => {
                    console.log("Saving edit with value:", input.value);
                    
                    const newValue = input.value.trim();
                    const row = this.closest('tr');
                    const expenseId = row.getAttribute('data-expense-id');
                    
                    console.log("Saving expense", expenseId, "field", type, "new value:", newValue);
                    
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
                    
                    console.log("Sending update data:", data);
                    
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
                        console.log("Edit response status:", response.status);
                        if (!response.ok) {
                            throw new Error(`HTTP error! status: ${response.status}`);
                        }
                        return response.json();
                    })
                    .then(result => {
                        console.log("Edit result:", result);
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
                        console.error('Edit fetch error:', error);
                        showMessage('Network error: ' + error.message, 'red');
                        this.innerHTML = originalHTML;
                    });
                };
                
                const cancelEdit = () => {
                    console.log("Canceling edit");
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
            });
        });
    }
    
    // Initialize everything
    setupDeleteButtons();
    setupEditableCells();
    
    console.log("Table setup complete!");
});