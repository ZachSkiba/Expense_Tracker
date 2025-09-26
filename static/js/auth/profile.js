// app/static/js/auth/profile.js - Profile page functionality

let deletionData = null;

// Profile field editing functions
function editField(fieldName) {
    // Hide all other edit forms
    const allItems = document.querySelectorAll('.info-item');
    allItems.forEach(item => {
        item.classList.remove('editing');
        const display = item.querySelector('.info-display');
        const form = item.querySelector('.edit-form');
        if (display) display.style.display = 'block';
        if (form) form.classList.remove('active');
    });
    
    // Show the selected field's edit form
    const item = document.getElementById(fieldName + '-item');
    const display = item.querySelector('.info-display');
    const form = item.querySelector('.edit-form');
    
    item.classList.add('editing');
    display.style.display = 'none';
    form.classList.add('active');
    
    // Focus the input
    const input = document.getElementById(fieldName + '-input');
    input.focus();
    input.select();
}

function cancelEdit(fieldName) {
    const item = document.getElementById(fieldName + '-item');
    const display = item.querySelector('.info-display');
    const form = item.querySelector('.edit-form');
    const input = document.getElementById(fieldName + '-input');
    const displayValue = document.getElementById(fieldName + '-display');
    
    // Reset input to original value
    input.value = displayValue.textContent;
    
    // Show display, hide form
    item.classList.remove('editing');
    display.style.display = 'block';
    form.classList.remove('active');
}

async function saveField(fieldName, event) {
    event.preventDefault();
    
    const input = document.getElementById(fieldName + '-input');
    const newValue = input.value.trim();
    
    if (!newValue) {
        alert('This field cannot be empty');
        return;
    }
    
    try {
        const formData = new FormData();
        formData.append('field', fieldName.replace('-', '_'));
        formData.append('value', newValue);
        
        // Get the update URL from window object (set by template)
        const response = await fetch(window.profileConfig.updateUrl, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Update display value
            const display = document.getElementById(fieldName + '-display');
            display.textContent = newValue;
            
            // Update header if it's the full name or email
            if (fieldName === 'full-name') {
                const profileName = document.querySelector('.profile-name');
                if (profileName) profileName.textContent = newValue;
            } else if (fieldName === 'email') {
                const profileEmail = document.querySelector('.profile-email');
                if (profileEmail) profileEmail.textContent = newValue;
            }
            
            // Hide edit form
            cancelEdit(fieldName);
            
            // Show success message
            showMessage('Profile updated successfully', 'success');
        } else {
            showMessage(result.error || 'Error updating profile', 'error');
        }
    } catch (error) {
        showMessage('Network error. Please try again.', 'error');
    }
}

// Flash message functions
function showMessage(text, type) {
    const messagesContainer = document.querySelector('.flash-messages');
    if (!messagesContainer) return;
    
    const message = document.createElement('div');
    message.className = `flash-message flash-${type}`;
    message.textContent = text;
    
    messagesContainer.appendChild(message);
    
    // Auto-hide after 3 seconds
    setTimeout(() => {
        message.classList.add('fade-out');
        setTimeout(() => {
            if (message.parentNode) {
                message.parentNode.removeChild(message);
            }
        }, 500);
    }, 3000);
}

// Auto-hide existing flash messages
function initFlashMessages() {
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(function(message) {
        setTimeout(function() {
            message.classList.add('fade-out');
            setTimeout(function() {
                if (message.parentNode) {
                    message.parentNode.removeChild(message);
                }
            }, 500);
        }, 3000);
    });
}

// Account deletion functions
async function initAccountDeletion() {
    const deleteBtn = document.getElementById('delete-account-btn');
    if (!deleteBtn) return;
    
    deleteBtn.addEventListener('click', async () => {
        try {
            const response = await fetch(window.profileConfig.deleteCheckUrl);
            deletionData = await response.json();
            
            showDeleteModal(deletionData);
        } catch (error) {
            showMessage('Error checking account deletion eligibility', 'error');
        }
    });
}

function showDeleteModal(data) {
    const modal = document.getElementById('delete-modal');
    const modalBody = document.getElementById('modal-body');
    
    if (!modal || !modalBody) return;
    
    let content = '';
    
    if (!data.can_delete) {
        content += '<div class="blocking-list">';
        content += '<h4>Cannot Delete Account</h4>';
        data.blocking_issues.forEach(issue => {
            content += `<div class="blocking-item">${issue}</div>`;
        });
        content += '</div>';
    } else {
        if (data.warnings.length > 0) {
            content += '<div class="warning-list">';
            content += '<h4>Important Information</h4>';
            data.warnings.forEach(warning => {
                content += `<div class="warning-item">${warning}</div>`;
            });
            content += '</div>';
        }
        
        content += '<div class="confirmation-section">';
        content += '<p><strong>To confirm deletion, type "delete my account" below:</strong></p>';
        content += '<input type="text" id="confirmation-input" class="confirmation-input" placeholder="delete my account">';
        content += '</div>';
    }
    
    modalBody.innerHTML = content;
    
    const confirmBtn = document.getElementById('confirm-delete');
    if (confirmBtn) {
        if (data.can_delete) {
            confirmBtn.style.display = 'inline-flex';
            const input = document.getElementById('confirmation-input');
            if (input) {
                input.addEventListener('input', () => {
                    confirmBtn.disabled = input.value.trim().toLowerCase() !== 'delete my account';
                });
            }
        } else {
            confirmBtn.style.display = 'none';
        }
    }
    
    modal.classList.add('show');
}

function initDeleteModal() {
    const cancelBtn = document.getElementById('cancel-delete');
    const confirmBtn = document.getElementById('confirm-delete');
    const modal = document.getElementById('delete-modal');
    
    if (cancelBtn) {
        cancelBtn.addEventListener('click', () => {
            if (modal) modal.classList.remove('show');
        });
    }
    
    if (confirmBtn) {
        confirmBtn.addEventListener('click', async () => {
            const spinner = confirmBtn.querySelector('.loading-spinner');
            
            confirmBtn.disabled = true;
            if (spinner) spinner.style.display = 'inline-block';
            
            try {
                const confirmationInput = document.getElementById('confirmation-input');
                const response = await fetch(window.profileConfig.deleteUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        confirmation: confirmationInput ? confirmationInput.value : ''
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    alert(result.message);
                    window.location.href = result.redirect_url;
                } else {
                    showMessage(result.error, 'error');
                    confirmBtn.disabled = false;
                    if (spinner) spinner.style.display = 'none';
                }
            } catch (error) {
                showMessage('Network error occurred', 'error');
                confirmBtn.disabled = false;
                if (spinner) spinner.style.display = 'none';
            }
        });
    }
    
    // Close modal when clicking outside
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target.id === 'delete-modal') {
                e.target.classList.remove('show');
            }
        });
    }
}

// Initialize everything when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initFlashMessages();
    initAccountDeletion();
    initDeleteModal();
});

// Make functions available globally for inline event handlers
window.editField = editField;
window.cancelEdit = cancelEdit;
window.saveField = saveField;