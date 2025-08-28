console.log("expenses_table.js loaded");

// Wait for DOM to be ready
document.addEventListener("DOMContentLoaded", function() {
    console.log("DOM ready, initializing table functionality");
    
    const tableError = document.getElementById('table-error');
    
    function showMessage(message, color) {
        console.log("Showing message:", message, color);
        if (tableError) {
            tableError.style.color = color || 'black';
            tableError.innerHTML = message;
            setTimeout(() => {
                tableError.innerHTML = '';
            }, 3000);
        }
    }

    // DELETE FUNCTIONALITY - Simple approach
    console.log("Setting up delete buttons");
    const deleteButtons = document.querySelectorAll('.delete-btn');
    console.log("Found", deleteButtons.length, "delete buttons");
    
    deleteButtons.forEach((btn, index) => {
        console.log(`Setting up delete button ${index}`);
        
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            console.log("Delete button clicked!");
            
            const row = this.closest('tr');
            const expenseId = row.getAttribute('data-expense-id') || this.getAttribute('data-expense-id');
            
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
            
            fetch(`/delete_expense/${expenseId}`, { 
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => {
                console.log("Delete response status:", response.status);
                return response.json();
            })
            .then(result => {
                console.log("Delete result:", result);
                if (result.success) {
                    row.remove();
                    showMessage('Expense deleted successfully!', 'green');
                } else {
                    showMessage(result.error || 'Error deleting expense', 'red');
                }
            })
            .catch(error => {
                console.error('Delete fetch error:', error);
                showMessage('Network error deleting expense', 'red');
            });
        });
    });

    // EDIT FUNCTIONALITY - Simple approach
    console.log("Setting up editable cells");
    const editableCells = document.querySelectorAll('td.editable');
    console.log("Found", editableCells.length, "editable cells");
    
    editableCells.forEach((cell, index) => {
        console.log(`Setting up editable cell ${index}`);
        
        cell.style.cursor = 'pointer';
        cell.style.backgroundColor = '#f9f9f9';
        cell.title = 'Click to edit';
        
        cell.addEventListener('click', function() {
            console.log("Editable cell clicked!");
            
            // Check if already editing
            if (this.querySelector('input, select')) {
                console.log("Already editing, ignoring");
                return;
            }
            
            const type = this.classList[1]; // amount, category, description, user, date
            const currentValue = this.getAttribute('data-value');
            const originalHTML = this.innerHTML;
            
            console.log("Starting edit - type:", type, "value:", currentValue);
            
            // Create input based on type
            let input;
            if (type === 'amount') {
                input = document.createElement('input');
                input.type = 'number';
                input.step = '0.01';
                input.min = '0.01';
                input.value = parseFloat(currentValue).toFixed(2);
            } else if (type === 'description') {
                input = document.createElement('input');
                input.type = 'text';
                input.value = currentValue;
            } else if (type === 'date') {
                input = document.createElement('input');
                input.type = 'date';
                input.value = currentValue;
            } else {
                // For category and user, just use text input for now (simple)
                input = document.createElement('input');
                input.type = 'text';
                input.value = currentValue;
            }
            
            // Style the input
            input.style.width = '100%';
            input.style.border = '2px solid blue';
            input.style.padding = '4px';
            
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
                
                // Prepare data
                const data = {};
                data[type] = newValue;
                
                console.log("Sending update data:", data);
                
                // Send to server
                fetch(`/edit_expense/${expenseId}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                })
                .then(response => {
                    console.log("Edit response status:", response.status);
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
                            this.innerHTML = newValue;
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
                    showMessage('Network error', 'red');
                    this.innerHTML = originalHTML;
                });
            };
            
            const cancelEdit = () => {
                console.log("Canceling edit");
                this.innerHTML = originalHTML;
            };
            
            // Event listeners
            input.addEventListener('blur', saveEdit);
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
    
    console.log("Table setup complete!");
});