const categories = {{ categories | tojson | safe }};
const users = {{ users | tojson | safe }};
const categoryNames = categories.map(c => c.name);
const userNames = users.map(u => u.name);

const tableError = document.getElementById('table-error');

function saveRow(row) {
    const expenseId = row.getAttribute('data-expense-id');
    const data = {};
    row.querySelectorAll('td.editable').forEach(cell => {
        let value = cell.getAttribute('data-value').trim();
        if (cell.classList.contains('amount')) {
            value = parseFloat(value);
            if (isNaN(value) || value < 0) value = 0;
            cell.innerText = `$${value.toFixed(2)}`;
            cell.setAttribute('data-value', value);
            data['amount'] = value;
        } else {
            data[cell.classList[1]] = value;
        }
    });

    fetch(`/edit_expense/${expenseId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
    .then(res => res.json())
    .then(result => {
        tableError.innerText = result.success ? '' : result.error;
    });
}

document.querySelectorAll('td.editable').forEach(cell => {
    cell.addEventListener('click', () => {
        if (cell.querySelector('input, select')) return;

        const type = cell.classList[1];
        const value = cell.getAttribute('data-value');
        let input;

        if (type === 'amount' || type === 'description' || type === 'date') {
            input = document.createElement('input');
            input.type = type === 'date' ? 'date' : 'text';
            input.value = type === 'amount' ? parseFloat(value).toFixed(2) : value;
            input.style.width = '100%';
        } else { // category or user
            input = document.createElement('select');
            const options = type === 'category' ? categoryNames : userNames;
            options.forEach(opt => {
                const option = document.createElement('option');
                option.value = opt;
                option.text = opt;
                if (opt === value) option.selected = true;
                input.appendChild(option);
            });

            // Add the manage option
            const manageOption = document.createElement('option');
            manageOption.value = "manage";
            manageOption.text = "➕ Add / Manage";
            input.appendChild(manageOption);

            // Handle redirect when "manage" is selected
            input.addEventListener('change', () => {
                if (input.value === "manage") {
                    const nextUrl = "{{ url_for('add_expense') }}"; // back to table
                    if (type === 'category') {
                        window.location.href = "{{ url_for('manage_categories') }}?next=" + encodeURIComponent(nextUrl);
                    } else if (type === 'user') {
                        window.location.href = "{{ url_for('manage_users') }}?next=" + encodeURIComponent(nextUrl);
                    }
                }
            });
        }

        cell.innerText = '';
        cell.appendChild(input);
        input.focus();

        // Description autocomplete
        if (type === 'description') {
            const suggBox = document.createElement('div');
            suggBox.classList.add('suggestions');
            cell.appendChild(suggBox);

            input.addEventListener('input', () => {
                const query = input.value.trim();
                suggBox.innerHTML = '';
                if (!query) return;

                fetch(`/store_suggestions?q=${encodeURIComponent(query)}`)
                    .then(res => res.json())
                    .then(data => {
                        data.suggestions.forEach(s => {
                            const div = document.createElement('div');
                            div.innerText = s;
                            div.addEventListener('mousedown', (e) => {
                                e.preventDefault(); 
                                input.value = s;
                                suggBox.innerHTML = '';
                                input.focus();
                                saveEdit();
                            });
                            suggBox.appendChild(div);
                        });
                    });
            });
        }

        function saveEdit() {
            let newValue = input.value.trim();
            if (type === 'amount') {
                newValue = parseFloat(newValue);
                if (isNaN(newValue) || newValue < 0) newValue = 0;
                cell.innerText = `$${newValue.toFixed(2)}`;
            } else {
                cell.innerText = newValue;
            }
            cell.setAttribute('data-value', newValue);
            saveRow(cell.closest('tr'));
        }

        input.addEventListener('blur', saveEdit);
        input.addEventListener('keydown', e => {
            if (e.key === 'Enter') {
                e.preventDefault();
                saveEdit();
            }
        });
    });
});

// Delete expense
function deleteExpense(expenseId) {
    if (!confirm("Are you sure you want to delete this expense?")) return;

    fetch(`/delete_expense/${expenseId}`, { method: 'POST' })
        .then(res => res.json())
        .then(result => {
            if(result.success){
                const row = document.querySelector(`tr[data-expense-id='${expenseId}']`);
                if(row) row.remove();
            } else {
                alert("Error deleting expense.");
            }
        });
}

document.querySelectorAll('.delete-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const row = btn.closest('tr');
        const expenseId = row.getAttribute('data-expense-id');
        deleteExpense(expenseId);
    });
});