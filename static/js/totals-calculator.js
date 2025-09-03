// Totals Calculator for Expenses and Payments Tables

class TotalsCalculator {
    constructor() {
        this.init();
    }

    init() {
        // Calculate totals when page loads
        this.calculateExpensesTotal();
        this.calculatePaymentsTotal();
        this.updatePaymentsCount();
        
        // Set up observers for dynamic updates
        this.observeTableChanges();
    }

    calculateExpensesTotal() {
        const totalElement = document.getElementById('expenses-total');
        
        if (!totalElement) return;

        let total = 0;
        
        // Try multiple selectors to find expense amounts
        const selectors = [
            '.expenses-table tbody td:first-child', // First column (amount)
            '.expenses-table tbody td.amount', // Amount class
            '.expenses-table tbody td:nth-child(1)', // First child
            'table tbody td:first-child', // Generic table first column
            '[data-amount]' // Data attribute
        ];
        
        for (const selector of selectors) {
            const amountCells = document.querySelectorAll(selector);
            if (amountCells.length > 0) {
                amountCells.forEach(cell => {
                    const amountText = cell.textContent.trim();
                    const amount = parseFloat(amountText.replace(/[$,]/g, ''));
                    if (!isNaN(amount)) {
                        total += amount;
                    }
                });
                break; // Use first selector that finds elements
            }
        }

        totalElement.textContent = this.formatCurrency(total);
    }

    calculatePaymentsTotal() {
        const totalElement = document.getElementById('payments-total');
        
        if (!totalElement) return;

        let total = 0;
        
        // Try multiple selectors to find payment amounts
        const selectors = [
            '.settlements-table-main tbody td.amount',
            '.settlements-table-main tbody td:nth-child(3)', // Amount column
            '.settlements-table-main .amount',
            '.settlements-table tbody td:first-child', // First column (amount)
            '.settlements-table tbody td.amount',
            '[data-amount]' // If amounts are stored in data attributes
        ];
        
        for (const selector of selectors) {
            const amountCells = document.querySelectorAll(selector);
            if (amountCells.length > 0) {
                amountCells.forEach(cell => {
                    const amountText = cell.textContent.trim();
                    const amount = parseFloat(amountText.replace(/[$,]/g, ''));
                    if (!isNaN(amount)) {
                        total += amount;
                    }
                });
                break; // Use first selector that finds elements
            }
        }

        totalElement.textContent = this.formatCurrency(total);
    }

    updatePaymentsCount() {
        const countElement = document.querySelector('.settlements-count');
        
        if (!countElement) return;

        let count = 0;
        
        // Try multiple selectors to find payment rows
        const selectors = [
            '.settlements-table-main tbody tr',
            '.settlements-table-main tr:not(:first-child)', // Exclude header
            '.settlements-table tbody tr',
            '.settlements-table tr:not(:first-child)', // Exclude header
            '[data-settlement-id]' // If rows have settlement IDs
        ];
        
        for (const selector of selectors) {
            const rows = document.querySelectorAll(selector);
            if (rows.length > 0) {
                // Filter out empty or "no payments" rows
                count = Array.from(rows).filter(row => {
                    const text = row.textContent.trim().toLowerCase();
                    return !text.includes('no payments') && !text.includes('loading') && text.length > 10;
                }).length;
                break;
            }
        }

        countElement.textContent = `(${count})`;
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 2
        }).format(amount);
    }

    observeTableChanges() {
        // Observer for expenses table
        const expensesTable = document.querySelector('.expenses-table tbody');
        if (expensesTable) {
            const expensesObserver = new MutationObserver(() => {
                this.calculateExpensesTotal();
            });
            expensesObserver.observe(expensesTable, {
                childList: true,
                subtree: true,
                characterData: true
            });
        }

        // Observer for payments table - try multiple containers
        const paymentsContainers = [
            document.getElementById('settlements-table-container'),
            document.querySelector('.settlements-table'),
            document.querySelector('.payments-section')
        ];
        
        for (const container of paymentsContainers) {
            if (container) {
                const paymentsObserver = new MutationObserver(() => {
                    // Delay calculation to ensure table is fully rendered
                    setTimeout(() => {
                        this.calculatePaymentsTotal();
                        this.updatePaymentsCount();
                    }, 100);
                });
                paymentsObserver.observe(container, {
                    childList: true,
                    subtree: true,
                    characterData: true
                });
                break; // Use first container found
            }
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new TotalsCalculator();
});

// Also initialize if script loads after DOM
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        new TotalsCalculator();
    });
} else {
    new TotalsCalculator();
}
