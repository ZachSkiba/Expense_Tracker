document.addEventListener("DOMContentLoaded", function() { 
    const categorySelect = document.getElementById("category-select");
    const descContainer = document.getElementById("category-desc-container");
    const userSelect = document.getElementById("user-select");
    const descInput = document.getElementById("category-description");
    const suggestionsContainer = document.getElementById("suggestions-container");

    // CATEGORY LOGIC
    if (categorySelect) {
        // Show description container on page load if a valid category is selected
        if (categorySelect.value && categorySelect.value !== "manage") {
            descContainer.style.display = "block";
        } else {
            descContainer.style.display = "none";
        }

        // Handle category changes
        categorySelect.addEventListener("change", function() {
            if (this.value === "manage") {
                // Remove required attributes to prevent validation from blocking redirect
                document.querySelectorAll('input[required], select[required]').forEach(el => {
                    el.removeAttribute('required');
                });
                
                // Redirect immediately
                const nextUrl = encodeURIComponent(window.location.href);
                window.location.href = `${urls.manageCategories}?next=${nextUrl}`;
                return false; // Prevent any further processing
            } else if (this.value) {
                descContainer.style.display = "block"; // Show description
            } else {
                descContainer.style.display = "none"; // Hide if nothing selected
            }
        });
    }

    // USER LOGIC
    if (userSelect) {
        userSelect.addEventListener("change", function() {
            if (this.value === "manage") {
                // Remove required attributes to prevent validation from blocking redirect
                document.querySelectorAll('input[required], select[required]').forEach(el => {
                    el.removeAttribute('required');
                });
                
                // Redirect immediately
                const nextUrl = encodeURIComponent(window.location.href);
                window.location.href = `${urls.manageUsers}?next=${nextUrl}`;
                return false; // Prevent any further processing
            }
        });
    }

    // Prevent form submission when manage options are selected
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', function(e) {
            if (categorySelect.value === "manage" || userSelect.value === "manage") {
                e.preventDefault();
                return false;
            }
        });
    }

    // DESCRIPTION AUTOCOMPLETE
    if (descInput && suggestionsContainer) {
        descInput.addEventListener("input", function() {
            const query = this.value.trim();
            if (!query) {
                suggestionsContainer.style.display = "none";
                return;
            }

            fetch(`/store_suggestions?q=${encodeURIComponent(query)}`)
                .then(res => res.json())
                .then(data => {
                    suggestionsContainer.innerHTML = "";
                    if (!data.suggestions.length) {
                        suggestionsContainer.style.display = "none";
                        return;
                    }

                    data.suggestions.forEach(s => {
                        const div = document.createElement("div");
                        div.textContent = s;
                        div.style.padding = "4px";
                        div.style.cursor = "pointer";
                        div.addEventListener("click", () => {
                            descInput.value = s;
                            suggestionsContainer.style.display = "none";
                        });
                        suggestionsContainer.appendChild(div);
                    });
                    suggestionsContainer.style.display = "block";
                });
        });

        // Hide suggestions if clicked outside
        document.addEventListener("click", function(e) {
            if (e.target !== descInput) {
                suggestionsContainer.style.display = "none";
            }
        });
    }
});