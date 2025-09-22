// app/js/modules/settings.js - Settings page JavaScript functionality

class SettingsManager {
    constructor() {
        this.isEditMode = false;
        this.originalValues = {};
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupDisabledToggles();
    }

    setupEventListeners() {
        // Make sure DOM is loaded
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setupEventListeners());
            return;
        }

        // Setup existing functionality
        this.setupDisabledToggles();
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
        const groupIndex = pathParts.indexOf('groups');
        
        if (groupIndex !== -1 && pathParts[groupIndex + 1]) {
            return pathParts[groupIndex + 1];
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