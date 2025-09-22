// app/js/modules/settings.js - Settings page JavaScript functionality with Leave and Delete Group

class SettingsManager {
    constructor() {
        this.isEditMode = false;
        this.originalValues = {};
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupDisabledToggles();
        this.setupLeaveConfirmation();
        this.setupDeleteConfirmation();
    }

    setupEventListeners() {
        // Make sure DOM is loaded
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setupEventListeners());
            return;
        }

        // Setup existing functionality
        this.setupDisabledToggles();
        this.setupLeaveConfirmation();
        this.setupDeleteConfirmation();
    }

    // Copy invite code functionality
    copyInviteCode() {
        const inviteCode = document.getElementById('inviteCode');
        const button = document.querySelector('.copy-button');
        
        if (!inviteCode || !button) {
            console.error('Invite code elements not found');
            return;
        }

        const codeText = inviteCode.textContent;
        
        // Use modern clipboard API with fallback
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(codeText)
                .then(() => this.showCopySuccess(button))
                .catch(err => {
                    console.error('Clipboard API failed:', err);
                    this.fallbackCopy(codeText, button);
                });
        } else {
            this.fallbackCopy(codeText, button);
        }
    }

    fallbackCopy(text, button) {
        try {
            const textArea = document.createElement('textarea');
            textArea.value = text;
            textArea.style.position = 'fixed';
            textArea.style.left = '-999999px';
            textArea.style.top = '-999999px';
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            this.showCopySuccess(button);
        } catch (err) {
            console.error('Fallback copy failed:', err);
            alert('Failed to copy invite code. Please copy it manually.');
        }
    }

    showCopySuccess(button) {
        const originalText = button.textContent;
        button.textContent = '✅ Copied!';
        button.classList.add('copied');
        
        setTimeout(() => {
            button.textContent = originalText;
            button.classList.remove('copied');
        }, 2000);
    }

    // Group editing functionality
    toggleEditMode() {
        const editBtn = document.getElementById('editToggleBtn');
        const editBtnText = document.getElementById('editBtnText');
        const editableItems = document.querySelectorAll('.editable-item');

        if (!editBtn || !editBtnText || !editableItems.length) {
            console.error('Edit mode elements not found');
            return;
        }

        if (!this.isEditMode) {
            this.enterEditMode(editBtn, editBtnText, editableItems);
        } else {
            this.saveChanges();
        }
    }

    enterEditMode(editBtn, editBtnText, editableItems) {
        this.isEditMode = true;
        editBtn.classList.add('editing');
        editBtnText.textContent = '💾 Save';

        // Store original values
        const groupNameEl = document.getElementById('groupName');
        const groupDescEl = document.getElementById('groupDescription');
        
        if (groupNameEl && groupDescEl) {
            this.originalValues.name = groupNameEl.textContent;
            this.originalValues.description = groupDescEl.textContent;
        }

        // Show edit inputs
        editableItems.forEach(item => {
            item.classList.add('edit-mode');
        });

        // Add click handlers for editable values
        this.setupEditHandlers();
    }

    setupEditHandlers() {
        const groupName = document.getElementById('groupName');
        const groupDesc = document.getElementById('groupDescription');
        const nameEdit = document.getElementById('groupNameEdit');
        const descEdit = document.getElementById('groupDescriptionEdit');

        if (groupName) {
            groupName.onclick = () => this.focusEdit('groupNameEdit');
        }
        if (groupDesc) {
            groupDesc.onclick = () => this.focusEdit('groupDescriptionEdit');
        }

        // Add keyboard handlers
        if (nameEdit) {
            nameEdit.addEventListener('keydown', (e) => this.handleKeyDown(e));
        }
        if (descEdit) {
            descEdit.addEventListener('keydown', (e) => this.handleKeyDown(e));
        }
    }

    focusEdit(inputId) {
        if (this.isEditMode) {
            const input = document.getElementById(inputId);
            if (input) {
                input.focus();
                // Select all text for easy replacement
                if (input.select) {
                    input.select();
                }
            }
        }
    }

    handleKeyDown(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            this.saveChanges();
        } else if (e.key === 'Escape') {
            this.cancelEdit();
        }
    }

    cancelEdit() {
        const editBtn = document.getElementById('editToggleBtn');
        const editBtnText = document.getElementById('editBtnText');
        const editableItems = document.querySelectorAll('.editable-item');

        if (!editBtn || !editBtnText) return;

        this.isEditMode = false;
        editBtn.classList.remove('editing');
        editBtnText.textContent = '✏️ Edit';

        // Restore original values
        const nameEdit = document.getElementById('groupNameEdit');
        const descEdit = document.getElementById('groupDescriptionEdit');
        
        if (nameEdit && this.originalValues.name) {
            nameEdit.value = this.originalValues.name;
        }
        if (descEdit && this.originalValues.description) {
            descEdit.value = this.originalValues.description === 'No description' ? '' : this.originalValues.description;
        }

        // Hide edit inputs
        editableItems.forEach(item => {
            item.classList.remove('edit-mode');
        });

        // Remove click handlers
        this.removeEditHandlers();
    }

    removeEditHandlers() {
        const groupName = document.getElementById('groupName');
        const groupDesc = document.getElementById('groupDescription');

        if (groupName) groupName.onclick = null;
        if (groupDesc) groupDesc.onclick = null;
    }

    async saveChanges() {
        const editBtn = document.getElementById('editToggleBtn');
        const editBtnText = document.getElementById('editBtnText');
        const nameEdit = document.getElementById('groupNameEdit');
        const descEdit = document.getElementById('groupDescriptionEdit');

        if (!editBtn || !editBtnText || !nameEdit || !descEdit) {
            console.error('Required elements not found for saving');
            return;
        }

        // Show saving state
        editBtn.classList.add('saving');
        editBtnText.innerHTML = '<span class="loading-spinner"></span>Saving...';

        const newName = nameEdit.value.trim();
        const newDescription = descEdit.value.trim();

        // Validate
        if (!newName) {
            alert('Group name cannot be empty');
            editBtn.classList.remove('saving');
            editBtnText.textContent = '💾 Save';
            nameEdit.focus();
            return;
        }

        if (newName.length > 100) {
            alert('Group name must be less than 100 characters');
            editBtn.classList.remove('saving');
            editBtnText.textContent = '💾 Save';
            nameEdit.focus();
            return;
        }

        if (newDescription.length > 500) {
            alert('Description must be less than 500 characters');
            editBtn.classList.remove('saving');
            editBtnText.textContent = '💾 Save';
            descEdit.focus();
            return;
        }

        try {
            // Get group ID from URL or data attribute
            const groupId = this.getGroupId();
            if (!groupId) {
                throw new Error('Group ID not found');
            }

            const response = await fetch(`/groups/${groupId}/update`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    name: newName,
                    description: newDescription
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            if (data.success) {
                // Update display values
                const groupNameEl = document.getElementById('groupName');
                const groupDescEl = document.getElementById('groupDescription');
                
                if (groupNameEl) groupNameEl.textContent = newName;
                if (groupDescEl) {
                    groupDescEl.textContent = newDescription || 'No description';
                }

                // Exit edit mode
                this.exitEditMode(editBtn, editBtnText);

                // Show success message briefly before refresh
                editBtnText.textContent = '✅ Saved!';
                
                // Auto-refresh to update everywhere
                setTimeout(() => {
                    window.location.reload();
                }, 1000);

            } else {
                throw new Error(data.error || 'Update failed');
            }

        } catch (error) {
            console.error('Error saving changes:', error);
            alert(`Failed to save changes: ${error.message}`);
            
            editBtn.classList.remove('saving');
            editBtnText.textContent = '💾 Save';
        }
    }

    exitEditMode(editBtn, editBtnText) {
        this.isEditMode = false;
        editBtn.classList.remove('editing', 'saving');
        
        const editableItems = document.querySelectorAll('.editable-item');
        editableItems.forEach(item => {
            item.classList.remove('edit-mode');
        });
        
        this.removeEditHandlers();
    }

    getGroupId() {
        // Try to get group ID from URL path
        if (window.groupId) return window.groupId;
        
        const pathParts = window.location.pathname.split('/');
        const settingsIndex = pathParts.indexOf('settings');
        
        if (settingsIndex !== -1 && pathParts[settingsIndex + 1]) {
            return pathParts[settingsIndex + 1];
        }

        // Alternative: try to get from data attribute or other source
        const settingsContainer = document.querySelector('[data-group-id]');
        if (settingsContainer) {
            return settingsContainer.dataset.groupId;
        }

        // Try to extract from any existing links
        const groupLink = document.querySelector('a[href*="/groups/"]');
        if (groupLink) {
            const matches = groupLink.href.match(/\/groups\/(\d+)/);
            if (matches) return matches[1];
        }

        return null;
    }

    // Setup disabled toggle interactions
    setupDisabledToggles() {
        const disabledToggles = document.querySelectorAll('.toggle-switch.disabled');
        
        disabledToggles.forEach(toggle => {
            toggle.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                
                // Visual feedback for disabled features
                const badge = toggle.parentElement.querySelector('.coming-soon-badge');
                if (badge) {
                    badge.style.transform = 'scale(1.1)';
                    badge.style.boxShadow = '0 2px 8px rgba(255, 181, 0, 0.5)';
                    
                    setTimeout(() => {
                        badge.style.transform = 'scale(1)';
                        badge.style.boxShadow = '0 1px 3px rgba(255, 181, 0, 0.3)';
                    }, 200);
                }
            });
        });
    }

    // LEAVE GROUP FUNCTIONALITY
    setupLeaveConfirmation() {
        const leaveConfirmInput = document.getElementById('leaveConfirmation');
        const confirmLeaveBtn = document.getElementById('confirmLeaveBtn');
        const newAdminSelect = document.getElementById('newAdminSelect');
        
        // Handle regular member confirmation input
        if (leaveConfirmInput && confirmLeaveBtn) {
            leaveConfirmInput.addEventListener('input', (e) => {
                const value = e.target.value.trim().toLowerCase();
                const isValid = value === 'leave';
                
                confirmLeaveBtn.disabled = !isValid;
                
                leaveConfirmInput.classList.remove('valid', 'invalid');
                if (value.length > 0) {
                    leaveConfirmInput.classList.add(isValid ? 'valid' : 'invalid');
                }
            });

            leaveConfirmInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !confirmLeaveBtn.disabled) {
                    this.confirmLeaveGroup();
                } else if (e.key === 'Escape') {
                    this.hideLeaveConfirmation();
                }
            });
        }

        // Handle admin selection for creator
        if (newAdminSelect && confirmLeaveBtn) {
            newAdminSelect.addEventListener('change', (e) => {
                const hasSelection = e.target.value !== '';
                confirmLeaveBtn.disabled = !hasSelection;
            });
        }

        // Handle modal close events
        const leaveModal = document.getElementById('leaveConfirmationModal');
        if (leaveModal) {
            leaveModal.addEventListener('click', (e) => {
                if (e.target === leaveModal) {
                    this.hideLeaveConfirmation();
                }
            });
        }
    }

    async showLeaveConfirmation() {
        const leaveButton = document.querySelector('.leave-group-button');
        
        // Show checking state
        if (leaveButton) {
            leaveButton.classList.add('checking');
            leaveButton.textContent = '🔍 Checking eligibility...';
        }

        // First check if user is eligible to leave
        try {
            const groupId = this.getGroupId();
            if (!groupId) {
                throw new Error('Group ID not found');
            }

            const response = await fetch(`/groups/${groupId}/check-leave-eligibility`, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }

            const eligibility = await response.json();

            if (!eligibility.can_leave) {
                this.showFinancialInvolvementModal(eligibility);
                return;
            }

            // User is eligible, show normal leave confirmation
            this.showLeaveModal();

        } catch (error) {
            console.error('Error checking leave eligibility:', error);
            alert(`Failed to check eligibility: ${error.message}`);
        } finally {
            // Reset button state
            if (leaveButton) {
                leaveButton.classList.remove('checking');
                leaveButton.textContent = '🚪 Leave Group';
            }
        }
    }

    showFinancialInvolvementModal(eligibility) {
        // Create a custom modal for financial involvement
        const existingModal = document.getElementById('financialInvolvementModal');
        if (existingModal) {
            existingModal.remove();
        }

        const modal = document.createElement('div');
        modal.id = 'financialInvolvementModal';
        modal.className = 'modal-overlay';
        modal.style.display = 'flex';

        modal.innerHTML = `
            <div class="modal-content leave-modal">
                <div class="modal-header">
                    <h2 class="modal-title">🚫 Cannot Leave Group</h2>
                </div>
                
                <div class="modal-body">
                    <div class="warning-message" style="background: linear-gradient(135deg, #fef2f2, #fee2e2); border-color: rgba(239, 68, 68, 0.2);">
                        <div class="warning-icon" style="color: #dc2626;">⚠️</div>
                        <div class="warning-text" style="color: #991b1b;">
                            <strong style="color: #dc2626;">You cannot leave this group due to financial involvement:</strong><br><br>
                            ${eligibility.details.map(detail => `• ${detail}`).join('<br>')}
                            <br><br>
                            <strong>To leave the group, you must:</strong><br>
                            • Settle all outstanding balances<br>
                            • Resolve all expense-related obligations<br>
                            • Clear all settlement history (if required by group policy)
                        </div>
                    </div>
                </div>

                <div class="modal-footer">
                    <button class="modal-btn modal-btn-cancel" onclick="this.closest('.modal-overlay').remove(); document.body.style.overflow = '';">
                        Understood
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        document.body.style.overflow = 'hidden';

        // Close on outside click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
                document.body.style.overflow = '';
            }
        });
    }

    showLeaveModal() {
        const modal = document.getElementById('leaveConfirmationModal');
        const leaveConfirmInput = document.getElementById('leaveConfirmation');
        const newAdminSelect = document.getElementById('newAdminSelect');
        const confirmLeaveBtn = document.getElementById('confirmLeaveBtn');
        
        if (!modal) {
            console.error('Leave confirmation modal not found');
            return;
        }

        // Reset modal state
        if (leaveConfirmInput) {
            leaveConfirmInput.value = '';
            leaveConfirmInput.classList.remove('valid', 'invalid');
        }
        
        if (newAdminSelect) {
            newAdminSelect.value = '';
        }
        
        if (confirmLeaveBtn) {
            confirmLeaveBtn.disabled = true;
            confirmLeaveBtn.classList.remove('loading');
            confirmLeaveBtn.textContent = '🚪 Leave Group';
        }

        // Show modal
        modal.style.display = 'flex';
        
        // Focus appropriate input
        setTimeout(() => {
            if (leaveConfirmInput) {
                leaveConfirmInput.focus();
            } else if (newAdminSelect) {
                newAdminSelect.focus();
            }
        }, 300);

        document.body.style.overflow = 'hidden';
    }

    hideLeaveConfirmation() {
        const modal = document.getElementById('leaveConfirmationModal');
        if (modal) {
            modal.style.display = 'none';
        }
        document.body.style.overflow = '';
    }

    async confirmLeaveGroup() {
        const confirmLeaveBtn = document.getElementById('confirmLeaveBtn');
        const leaveConfirmInput = document.getElementById('leaveConfirmation');
        const newAdminSelect = document.getElementById('newAdminSelect');
        
        if (!confirmLeaveBtn) {
            console.error('Leave confirmation button not found');
            return;
        }

        // Validate based on user type
        let newAdminId = null;
        
        if (newAdminSelect) {
            // Creator must select new admin
            newAdminId = newAdminSelect.value;
            if (!newAdminId) {
                alert('Please select a new admin before leaving');
                newAdminSelect.focus();
                return;
            }
        } else if (leaveConfirmInput) {
            // Regular member must type confirmation
            const confirmationText = leaveConfirmInput.value.trim().toLowerCase();
            if (confirmationText !== 'leave') {
                alert('Please type "leave" to confirm');
                leaveConfirmInput.focus();
                return;
            }
        }

        // Show loading state
        confirmLeaveBtn.classList.add('loading');
        confirmLeaveBtn.disabled = true;
        confirmLeaveBtn.textContent = 'Leaving...';

        try {
            const groupId = this.getGroupId();
            if (!groupId) {
                throw new Error('Group ID not found');
            }

            const requestData = {};
            if (newAdminId) {
                requestData.new_admin_id = newAdminId;
            }

            const response = await fetch(`/groups/${groupId}/leave`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify(requestData)
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data.success) {
                // Show success state
                confirmLeaveBtn.classList.remove('loading');
                confirmLeaveBtn.classList.add('leave-success');
                confirmLeaveBtn.textContent = 'Left Successfully!';

                // Show success message
                alert(data.message || 'You have left the group successfully');

                // Redirect to dashboard
                setTimeout(() => {
                    window.location.href = data.redirect_url || '/dashboard';
                }, 1000);

            } else {
                throw new Error(data.error || 'Leave failed');
            }

        } catch (error) {
            console.error('Error leaving group:', error);
            
            // Reset button state
            confirmLeaveBtn.classList.remove('loading');
            confirmLeaveBtn.textContent = '🚪 Leave Group';
            
            // Show error
            alert(`Failed to leave group: ${error.message}`);
            
            // Re-enable button based on validation
            if (newAdminSelect) {
                confirmLeaveBtn.disabled = !newAdminSelect.value;
            } else if (leaveConfirmInput) {
                const isValid = leaveConfirmInput.value.trim().toLowerCase() === 'leave';
                confirmLeaveBtn.disabled = !isValid;
            }
        }
    }

    // DELETE GROUP FUNCTIONALITY
    setupDeleteConfirmation() {
        const confirmInput = document.getElementById('deleteConfirmation');
        const confirmBtn = document.getElementById('confirmDeleteBtn');
        
        if (confirmInput && confirmBtn) {
            confirmInput.addEventListener('input', (e) => {
                const value = e.target.value.trim().toLowerCase();
                const isValid = value === 'delete';
                
                // Update button state
                confirmBtn.disabled = !isValid;
                
                // Update input styling
                confirmInput.classList.remove('valid', 'invalid');
                if (value.length > 0) {
                    confirmInput.classList.add(isValid ? 'valid' : 'invalid');
                }
            });

            // Handle Enter key in confirmation input
            confirmInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !confirmBtn.disabled) {
                    this.confirmDeleteGroup();
                } else if (e.key === 'Escape') {
                    this.hideDeleteConfirmation();
                }
            });
        }

        // Close modal when clicking outside
        const modal = document.getElementById('deleteConfirmationModal');
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.hideDeleteConfirmation();
                }
            });
        }

        // Handle Escape key globally
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const leaveModal = document.getElementById('leaveConfirmationModal');
                if (leaveModal && leaveModal.style.display !== 'none') {
                    this.hideLeaveConfirmation();
                    return;
                }
                
                const deleteModal = document.getElementById('deleteConfirmationModal');
                if (deleteModal && deleteModal.style.display !== 'none') {
                    this.hideDeleteConfirmation();
                }
            }
        });
    }

    showDeleteConfirmation() {
        const modal = document.getElementById('deleteConfirmationModal');
        const confirmInput = document.getElementById('deleteConfirmation');
        const confirmBtn = document.getElementById('confirmDeleteBtn');
        
        if (!modal) {
            console.error('Delete confirmation modal not found');
            return;
        }

        // Reset modal state
        if (confirmInput) {
            confirmInput.value = '';
            confirmInput.classList.remove('valid', 'invalid');
        }
        if (confirmBtn) {
            confirmBtn.disabled = true;
            confirmBtn.classList.remove('loading');
            confirmBtn.textContent = '🗑️ Delete Group Forever';
        }

        // Show modal with animation
        modal.style.display = 'flex';
        
        // Focus on input after animation
        setTimeout(() => {
            if (confirmInput) {
                confirmInput.focus();
            }
        }, 300);

        // Prevent body scroll
        document.body.style.overflow = 'hidden';
    }

    hideDeleteConfirmation() {
        const modal = document.getElementById('deleteConfirmationModal');
        if (modal) {
            modal.style.display = 'none';
        }
        
        // Re-enable body scroll
        document.body.style.overflow = '';
    }

    async confirmDeleteGroup() {
        const confirmBtn = document.getElementById('confirmDeleteBtn');
        const confirmInput = document.getElementById('deleteConfirmation');
        
        if (!confirmBtn || !confirmInput) {
            console.error('Delete confirmation elements not found');
            return;
        }

        // Validate confirmation text
        const confirmationText = confirmInput.value.trim().toLowerCase();
        if (confirmationText !== 'delete') {
            alert('Please type "delete" to confirm deletion');
            confirmInput.focus();
            return;
        }

        // Show loading state
        confirmBtn.classList.add('loading');
        confirmBtn.disabled = true;
        confirmBtn.textContent = 'Deleting...';

        try {
            const groupId = this.getGroupId();
            if (!groupId) {
                throw new Error('Group ID not found');
            }

            const response = await fetch(`/groups/${groupId}/delete`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    confirmation: confirmationText
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data.success) {
                // Show success state
                confirmBtn.classList.remove('loading');
                confirmBtn.classList.add('delete-success');
                confirmBtn.textContent = 'Deleted Successfully!';

                // Show success message
                alert(data.message || 'Group deleted successfully');

                // Redirect to dashboard
                setTimeout(() => {
                    window.location.href = data.redirect_url || '/dashboard';
                }, 1000);

            } else {
                throw new Error(data.error || 'Delete failed');
            }

        } catch (error) {
            console.error('Error deleting group:', error);
            
            // Reset button state
            confirmBtn.classList.remove('loading');
            confirmBtn.disabled = false;
            confirmBtn.textContent = '🗑️ Delete Group Forever';
            
            // Show error
            alert(`Failed to delete group: ${error.message}`);
            
            // Re-enable the button based on input
            const isValid = confirmInput.value.trim().toLowerCase() === 'delete';
            confirmBtn.disabled = !isValid;
        }
    }

    // Utility method for debugging
    log(message, data = null) {
        if (window.location.hostname === 'localhost' || window.location.hostname.includes('127.0.0.1')) {
            console.log(`[Settings] ${message}`, data || '');
        }
    }
}

// Global functions for HTML onclick handlers
window.settingsManager = new SettingsManager();

// Export functions to global scope for HTML compatibility
window.copyInviteCode = () => window.settingsManager.copyInviteCode();
window.toggleEditMode = () => window.settingsManager.toggleEditMode();
window.showLeaveConfirmation = () => window.settingsManager.showLeaveConfirmation();
window.hideLeaveConfirmation = () => window.settingsManager.hideLeaveConfirmation();
window.confirmLeaveGroup = () => window.settingsManager.confirmLeaveGroup();
window.showDeleteConfirmation = () => window.settingsManager.showDeleteConfirmation();
window.hideDeleteConfirmation = () => window.settingsManager.hideDeleteConfirmation();
window.confirmDeleteGroup = () => window.settingsManager.confirmDeleteGroup();