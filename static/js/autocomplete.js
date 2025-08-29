// Shared autocomplete functionality
function createAutocomplete(input, containerId = null) {
    // Create suggestions container if not provided
    let suggestionsContainer;
    if (containerId) {
        suggestionsContainer = document.getElementById(containerId);
    } else {
        suggestionsContainer = document.createElement('div');
        suggestionsContainer.id = 'dynamic-suggestions';
        suggestionsContainer.style.cssText = 'border:1px solid #ccc; display:none; max-height:150px; overflow-y:auto; position:absolute; background:white; z-index:1000; width:100%; box-sizing:border-box;';
        
        // Position suggestions below the input
        const inputRect = input.getBoundingClientRect();
        console.log("Input position:", inputRect);
        
        // Ensure we have valid dimensions
        if (inputRect.width > 0 && inputRect.height > 0) {
            suggestionsContainer.style.top = (inputRect.bottom + window.scrollY) + 'px';
            suggestionsContainer.style.left = inputRect.left + 'px';
            suggestionsContainer.style.width = inputRect.width + 'px';
            console.log("Container positioned at:", {
                top: (inputRect.bottom + window.scrollY) + 'px',
                left: inputRect.left + 'px',
                width: inputRect.width + 'px'
            });
        } else {
            // Fallback positioning if input dimensions are not yet available
            console.log("Input dimensions not available, using fallback positioning");
            const inputStyle = window.getComputedStyle(input);
            const inputWidth = input.offsetWidth || parseInt(inputStyle.width) || 200;
            
            suggestionsContainer.style.top = (input.offsetTop + input.offsetHeight + window.scrollY) + 'px';
            suggestionsContainer.style.left = input.offsetLeft + 'px';
            suggestionsContainer.style.width = inputWidth + 'px';
            console.log("Fallback positioning:", {
                top: (input.offsetTop + input.offsetHeight + window.scrollY) + 'px',
                left: input.offsetLeft + 'px',
                width: inputWidth + 'px'
            });
        }
        
        // Add to page
         document.body.appendChild(suggestionsContainer);    
             
        // Force a reflow to ensure positioning is correct
        suggestionsContainer.offsetHeight;
    }
    
    // Autocomplete functionality
    input.addEventListener('input', function() {
        const query = this.value.trim();
        if (!query) {
            suggestionsContainer.style.display = 'none';
            return;
        }
        
        fetch(`/store_suggestions?q=${encodeURIComponent(query)}`)
            .then(res => res.json())
            .then(data => {
                suggestionsContainer.innerHTML = '';
                if (!data.suggestions.length) {
                    suggestionsContainer.style.display = 'none';
                    return;
                }
                
                data.suggestions.forEach(s => {
                    const div = document.createElement('div');
                    div.textContent = s;
                    div.style.cssText = 'padding:4px; cursor:pointer; border-bottom:1px solid #eee;';
                    div.addEventListener('click', () => {
                        input.value = s;
                        suggestionsContainer.style.display = 'none';
                        input.focus();
                    });
                    div.addEventListener('mouseenter', () => {
                        div.style.backgroundColor = '#f0f0f0';
                    });
                    div.addEventListener('mouseleave', () => {
                        div.style.backgroundColor = 'white';
                    });
                    suggestionsContainer.appendChild(div);
                });
                suggestionsContainer.style.display = 'block';
            });
    });
    
    // Hide suggestions when clicking outside
    const hideSuggestions = (e) => {
        if (e.target !== input && !suggestionsContainer.contains(e.target)) {
            suggestionsContainer.style.display = 'none';
        }
    };
    document.addEventListener('click', hideSuggestions);
    
    // Return cleanup function
    return {
        cleanup: () => {
            if (suggestionsContainer.id === 'dynamic-suggestions' && suggestionsContainer.parentNode) {
                suggestionsContainer.parentNode.removeChild(suggestionsContainer);
            }
            document.removeEventListener('click', hideSuggestions);
        }
    };
}

// Ensure function is available globally
window.createAutocomplete = createAutocomplete;
