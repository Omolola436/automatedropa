// Privacy ROPA System - Client-side JavaScript

// Global application object
const ROPAApp = {
    init: function() {
        this.setupEventListeners();
        this.initializeTooltips();
        this.setupFormValidation();
        this.initializeDataTables();
        this.setupAutoSave();
    },

    // Setup global event listeners
    setupEventListeners: function() {
        // Global form submission handling
        document.addEventListener('submit', function(e) {
            const form = e.target;
            if (form.tagName === 'FORM') {
                ROPAApp.handleFormSubmission(form);
            }
        });

        // Global click handlers
        document.addEventListener('click', function(e) {
            // Handle delete confirmations
            if (e.target.closest('a[href*="delete"]') || e.target.closest('button[data-action="delete"]')) {
                if (!confirm('Are you sure you want to delete this item? This action cannot be undone.')) {
                    e.preventDefault();
                }
            }

            // Handle status updates
            if (e.target.closest('a[href*="update_status"]')) {
                const link = e.target.closest('a');
                const status = link.href.split('/').pop();
                const action = status === 'Approved' ? 'approve' : 'reject';
                if (!confirm(`Are you sure you want to ${action} this record?`)) {
                    e.preventDefault();
                }
            }
        });

        // Setup responsive table handling
        this.setupResponsiveTables();
    },

    // Initialize Bootstrap tooltips
    initializeTooltips: function() {
        if (typeof bootstrap !== 'undefined') {
            const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
            tooltipTriggerList.map(function(tooltipTriggerEl) {
                return new bootstrap.Tooltip(tooltipTriggerEl);
            });
        }
    },

    // Enhanced form validation
    setupFormValidation: function() {
        const forms = document.querySelectorAll('form[data-validate="true"], .needs-validation');
        
        forms.forEach(function(form) {
            form.addEventListener('submit', function(e) {
                if (!form.checkValidity()) {
                    e.preventDefault();
                    e.stopPropagation();
                    ROPAApp.showValidationErrors(form);
                }
                form.classList.add('was-validated');
            });
        });
    },

    // Show validation errors
    showValidationErrors: function(form) {
        const invalidFields = form.querySelectorAll(':invalid');
        if (invalidFields.length > 0) {
            const firstInvalid = invalidFields[0];
            firstInvalid.focus();
            
            // Show custom error message
            const fieldName = firstInvalid.labels?.[0]?.textContent || firstInvalid.name || 'This field';
            this.showAlert(`${fieldName} is required or invalid.`, 'warning');
        }
    },

    // Handle form submissions with loading states
    handleFormSubmission: function(form) {
        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) {
            const originalText = submitBtn.innerHTML;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processing...';
            submitBtn.disabled = true;

            // Re-enable button after form submission (for cases where form doesn't redirect)
            setTimeout(function() {
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
            }, 3000);
        }
    },

    // Initialize enhanced data tables
    initializeDataTables: function() {
        const tables = document.querySelectorAll('.data-table, #ropaTable, #auditTable');
        
        tables.forEach(function(table) {
            if (table.rows.length > 1) {
                ROPAApp.enhanceTable(table);
            }
        });
    },

    // Enhance table functionality
    enhanceTable: function(table) {
        // Add search functionality
        this.addTableSearch(table);
        
        // Add sorting functionality
        this.addTableSorting(table);
        
        // Add row highlighting
        this.addTableRowHighlighting(table);
    },

    // Add search functionality to tables
    addTableSearch: function(table) {
        const tableContainer = table.parentElement;
        
        // Check if search already exists
        if (tableContainer.querySelector('.table-search')) {
            return;
        }

        const searchContainer = document.createElement('div');
        searchContainer.className = 'table-search mb-3';
        searchContainer.innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    <div class="input-group">
                        <span class="input-group-text">
                            <i class="fas fa-search"></i>
                        </span>
                        <input type="text" class="form-control" placeholder="Search table..." id="search-${table.id || 'table'}">
                    </div>
                </div>
                <div class="col-md-6 text-end">
                    <small class="text-muted">
                        Showing <span class="visible-rows">${table.rows.length - 1}</span> of <span class="total-rows">${table.rows.length - 1}</span> records
                    </small>
                </div>
            </div>
        `;

        tableContainer.insertBefore(searchContainer, table);

        const searchInput = searchContainer.querySelector('input');
        searchInput.addEventListener('keyup', function() {
            ROPAApp.filterTable(table, this.value);
        });
    },

    // Filter table rows based on search term
    filterTable: function(table, searchTerm) {
        const rows = table.querySelectorAll('tbody tr');
        const searchLower = searchTerm.toLowerCase();
        let visibleCount = 0;

        rows.forEach(function(row) {
            const text = row.textContent.toLowerCase();
            const isVisible = text.includes(searchLower);
            row.style.display = isVisible ? '' : 'none';
            if (isVisible) visibleCount++;
        });

        // Update count display
        const container = table.closest('.card-body') || table.parentElement;
        const visibleSpan = container.querySelector('.visible-rows');
        if (visibleSpan) {
            visibleSpan.textContent = visibleCount;
        }
    },

    // Add sorting functionality to tables
    addTableSorting: function(table) {
        const headers = table.querySelectorAll('thead th');
        
        headers.forEach(function(header, index) {
            if (header.textContent.trim() && !header.querySelector('.no-sort')) {
                header.style.cursor = 'pointer';
                header.title = 'Click to sort';
                
                header.addEventListener('click', function() {
                    ROPAApp.sortTable(table, index);
                });
            }
        });
    },

    // Sort table by column
    sortTable: function(table, columnIndex) {
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        const header = table.querySelectorAll('thead th')[columnIndex];
        
        // Determine sort direction
        const isAscending = !header.classList.contains('sort-desc');
        
        // Clear all sort classes
        table.querySelectorAll('thead th').forEach(h => {
            h.classList.remove('sort-asc', 'sort-desc');
        });
        
        // Add sort class to current header
        header.classList.add(isAscending ? 'sort-asc' : 'sort-desc');
        
        // Sort rows
        rows.sort(function(a, b) {
            const aText = a.cells[columnIndex]?.textContent.trim() || '';
            const bText = b.cells[columnIndex]?.textContent.trim() || '';
            
            // Check if values are numbers
            const aNum = parseFloat(aText);
            const bNum = parseFloat(bText);
            
            if (!isNaN(aNum) && !isNaN(bNum)) {
                return isAscending ? aNum - bNum : bNum - aNum;
            }
            
            // String comparison
            return isAscending ? 
                aText.localeCompare(bText) : 
                bText.localeCompare(aText);
        });
        
        // Reorder rows in DOM
        rows.forEach(row => tbody.appendChild(row));
    },

    // Add row highlighting on hover
    addTableRowHighlighting: function(table) {
        const rows = table.querySelectorAll('tbody tr');
        
        rows.forEach(function(row) {
            row.addEventListener('mouseenter', function() {
                this.style.backgroundColor = 'var(--bs-gray-100)';
            });
            
            row.addEventListener('mouseleave', function() {
                this.style.backgroundColor = '';
            });
        });
    },

    // Setup responsive table handling
    setupResponsiveTables: function() {
        const tables = document.querySelectorAll('.table-responsive table');
        
        tables.forEach(function(table) {
            // Add mobile-friendly attributes
            const headers = table.querySelectorAll('thead th');
            const rows = table.querySelectorAll('tbody tr');
            
            rows.forEach(function(row) {
                const cells = row.querySelectorAll('td');
                cells.forEach(function(cell, index) {
                    if (headers[index]) {
                        cell.setAttribute('data-label', headers[index].textContent);
                    }
                });
            });
        });
    },

    // Auto-save functionality for forms
    setupAutoSave: function() {
        const forms = document.querySelectorAll('form[data-autosave="true"]');
        
        forms.forEach(function(form) {
            let saveTimeout;
            
            form.addEventListener('input', function(e) {
                if (saveTimeout) {
                    clearTimeout(saveTimeout);
                }
                
                saveTimeout = setTimeout(function() {
                    ROPAApp.autoSaveForm(form);
                }, 2000); // Save after 2 seconds of inactivity
            });
        });
    },

    // Auto-save form data to localStorage
    autoSaveForm: function(form) {
        const formData = new FormData(form);
        const data = {};
        
        for (let [key, value] of formData.entries()) {
            data[key] = value;
        }
        
        const formId = form.id || 'form-autosave';
        localStorage.setItem(`autosave-${formId}`, JSON.stringify(data));
        
        // Show save indicator
        this.showSaveIndicator();
    },

    // Show save indicator
    showSaveIndicator: function() {
        const indicator = document.createElement('div');
        indicator.className = 'alert alert-success position-fixed';
        indicator.style.cssText = 'top: 20px; right: 20px; z-index: 9999; padding: 0.5rem 1rem;';
        indicator.innerHTML = '<i class="fas fa-check me-2"></i>Auto-saved';
        
        document.body.appendChild(indicator);
        
        setTimeout(function() {
            indicator.remove();
        }, 2000);
    },

    // Restore auto-saved form data
    restoreFormData: function(formId) {
        const saved = localStorage.getItem(`autosave-${formId}`);
        if (saved) {
            const data = JSON.parse(saved);
            const form = document.getElementById(formId);
            
            if (form) {
                Object.keys(data).forEach(function(key) {
                    const field = form.querySelector(`[name="${key}"]`);
                    if (field) {
                        if (field.type === 'checkbox' || field.type === 'radio') {
                            field.checked = field.value === data[key];
                        } else {
                            field.value = data[key];
                        }
                    }
                });
            }
        }
    },

    // Show alert messages
    showAlert: function(message, type = 'info', duration = 5000) {
        const alertContainer = document.querySelector('.alert-container') || document.body;
        
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        alert.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        alertContainer.appendChild(alert);
        
        // Auto-dismiss
        setTimeout(function() {
            if (alert.parentElement) {
                alert.remove();
            }
        }, duration);
    },

    // Progress tracking for forms
    trackFormProgress: function(formId) {
        const form = document.getElementById(formId);
        if (!form) return;
        
        const updateProgress = function() {
            const requiredFields = form.querySelectorAll('input[required], select[required], textarea[required]');
            const checkboxGroups = ['data_categories', 'data_subjects'];
            
            let filled = 0;
            let total = requiredFields.length + checkboxGroups.length;
            
            // Check regular required fields
            requiredFields.forEach(field => {
                if (field.value.trim() !== '') {
                    filled++;
                }
            });
            
            // Check required checkbox groups
            checkboxGroups.forEach(groupName => {
                const checkboxes = form.querySelectorAll(`input[name="${groupName}"]:checked`);
                if (checkboxes.length > 0) {
                    filled++;
                }
            });
            
            const percentage = Math.round((filled / total) * 100);
            const progressBar = document.getElementById('formProgress');
            const progressText = document.getElementById('progressText');
            
            if (progressBar) {
                progressBar.style.width = percentage + '%';
                progressBar.setAttribute('aria-valuenow', percentage);
            }
            
            if (progressText) {
                progressText.textContent = percentage + '%';
            }
        };
        
        // Update progress on form changes
        form.addEventListener('input', updateProgress);
        form.addEventListener('change', updateProgress);
        
        // Initial calculation
        updateProgress();
    },

    // Filter records by status (for dashboard cards)
    filterRecords: function(status) {
        // Trigger the appropriate filter button
        const filterButtons = document.querySelectorAll('input[name="statusFilter"]');
        filterButtons.forEach(button => {
            if (button.value === status) {
                button.checked = true;
                button.dispatchEvent(new Event('change'));
            }
        });
        
        // Scroll to records table
        const recordsTable = document.getElementById('records-table');
        if (recordsTable) {
            recordsTable.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    },

    // Utility functions
    utils: {
        // Format date for display
        formatDate: function(dateString) {
            if (!dateString) return 'N/A';
            const date = new Date(dateString);
            return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        },
        
        // Format file size
        formatFileSize: function(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        },
        
        // Debounce function
        debounce: function(func, wait) {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        }
    }
};

// Initialize application when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    ROPAApp.init();
    
    // Initialize progress tracking for ROPA forms
    if (document.getElementById('ropaForm') || document.getElementById('ropaEditForm')) {
        ROPAApp.trackFormProgress('ropaForm') || ROPAApp.trackFormProgress('ropaEditForm');
    }
    
    // Restore auto-saved data if available
    const forms = document.querySelectorAll('form[data-autosave="true"]');
    forms.forEach(function(form) {
        if (form.id) {
            ROPAApp.restoreFormData(form.id);
        }
    });
});

// Export for global use
window.ROPAApp = ROPAApp;

// Global function for dashboard card filtering
function filterRecords(status) {
    ROPAApp.filterRecords(status);
}
