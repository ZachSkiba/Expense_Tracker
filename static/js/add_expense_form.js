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
                const nextUrl = encodeURIComponent(urls.addExpense);
                window.location.href = `${urls.manageCategories}?next=${nextUrl}`;
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
                const nextUrl = encodeURIComponent(urls.addExpense);
                window.location.href = `${urls.manageUsers}?next=${nextUrl}`;
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
