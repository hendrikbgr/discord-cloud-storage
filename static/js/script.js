document.getElementById('uploadForm').addEventListener('submit', function() {
    var btn = document.getElementById('uploadBtn');
    var text = document.getElementById('uploadBtnText');
    var spinner = document.getElementById('uploadSpinner');

    // Replace text with spinner and disable button
    text.style.display = 'none';
    spinner.style.display = '';
    btn.disabled = true;
});

function searchFiles() {
    var input, filter, table, tr, td, i, txtValue;
    input = document.getElementById('searchInput');
    filter = input.value.toUpperCase();
    table = document.getElementById('fileTable');
    tr = table.getElementsByTagName('tr');

    for (i = 0; i < tr.length; i++) {
        // Get the first cell (ID)
        tdId = tr[i].getElementsByTagName('td')[1];
        // Get the second cell (File Name)
        tdName = tr[i].getElementsByTagName('td')[2];

        if (tdId || tdName) {
            txtValueId = tdId ? tdId.textContent || tdId.innerText : "";
            txtValueName = tdName ? tdName.textContent || tdName.innerText : "";

            if (txtValueId.toUpperCase().indexOf(filter) > -1 || txtValueName.toUpperCase().indexOf(filter) > -1) {
                tr[i].style.display = '';
            } else {
                tr[i].style.display = 'none';
            }
        }
    }
}


function sortTable(columnIndex) {
    var table, rows, switching, i, x, y, shouldSwitch, dir, switchCount = 0;
    table = document.getElementById("fileTable");
    switching = true;
    // Set the sorting direction to ascending initially
    dir = "asc";

    while (switching) {
        switching = false;
        rows = table.rows;
        for (i = 1; i < (rows.length - 1); i++) {
            shouldSwitch = false;
            x = rows[i].getElementsByTagName("TD")[columnIndex];
            y = rows[i + 1].getElementsByTagName("TD")[columnIndex];

            // Check if the rows should switch place, depending on the direction
            if (dir == "asc") {
                if (x.innerHTML.toLowerCase() > y.innerHTML.toLowerCase()) {
                    shouldSwitch = true;
                    break;
                }
            } else if (dir == "desc") {
                if (x.innerHTML.toLowerCase() < y.innerHTML.toLowerCase()) {
                    shouldSwitch = true;
                    break;
                }
            }
        }
        if (shouldSwitch) {
            rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
            switching = true;
            switchCount++;
        } else {
            if (switchCount == 0 && dir == "asc") {
                dir = "desc";
                switching = true;
            }
        }
    }
}

document.addEventListener('DOMContentLoaded', (event) => {
    setTimeout(function() {
        let alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            // Add the fade-out class
            alert.classList.add('alert-fading-out');

            // Wait for the fade-out to finish before closing
            setTimeout(() => {
                new bootstrap.Alert(alert).close();
            }, 500); // This should match the duration in the CSS
        });
    }, 2000); // Time before starting the fade-out
});

// Function to toggle all file checkboxes based on the state of the "select all" checkbox
function toggleTableCheckboxes(selectAllCheckbox) {
    // Get all file checkboxes in the table
    const checkboxes = document.querySelectorAll('.file-checkbox');
    // Set each file checkbox's checked status to match the "select all" checkbox
    checkboxes.forEach(checkbox => {
        checkbox.checked = selectAllCheckbox.checked;
    });
}

// Function to toggle the "select all" checkbox based on individual checkbox changes
function updateSelectAllCheckbox() {
    const allCheckboxes = document.querySelectorAll('.file-checkbox');
    const selectAllCheckbox = document.getElementById('selectAllCheckbox');
    // Check if all file checkboxes are checked
    selectAllCheckbox.checked = Array.from(allCheckboxes).every(checkbox => checkbox.checked);
    // If not all are checked, also ensure the "select all" checkbox is not checked
    if (!selectAllCheckbox.checked) {
        // Check if any file checkboxes are checked
        const anyChecked = Array.from(allCheckboxes).some(checkbox => checkbox.checked);
        // Indeterminate state when some but not all checkboxes are checked
        selectAllCheckbox.indeterminate = anyChecked;
    } else {
        // No indeterminate state when all are checked
        selectAllCheckbox.indeterminate = false;
    }
}

// Function to toggle select all / deselect all for checkboxes
function toggleSelectAll() {
    const allCheckboxes = document.querySelectorAll('.file-checkbox');
    const selectAllCheckbox = document.getElementById('selectAllCheckbox');
    // Determine if we are selecting all or deselecting all
    const selectAll = !Array.from(allCheckboxes).every(checkbox => checkbox.checked);
    // Set all checkboxes to the new state
    allCheckboxes.forEach(checkbox => {
        checkbox.checked = selectAll;
    });
    // Update the state of the "select all" checkbox
    selectAllCheckbox.checked = selectAll;
    selectAllCheckbox.indeterminate = false; // Remove indeterminate state when manually toggling
}

// Add event listeners to file checkboxes to update the "select all" checkbox appropriately
document.addEventListener('DOMContentLoaded', () => {
    const fileCheckboxes = document.querySelectorAll('.file-checkbox');
    fileCheckboxes.forEach(checkbox => {
        // When a checkbox is clicked, update the "select all" checkbox
        checkbox.addEventListener('change', updateSelectAllCheckbox);
    });
});

function startExport() {
    const selectedIds = Array.from(document.querySelectorAll('.file-checkbox:checked')).map(cb => cb.getAttribute('data-file-id'));
    
    fetch('/export', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: 'selected_ids[]=' + selectedIds.join('&selected_ids[]=')
    })
    .then(response => {
        if (response.ok) return response.blob();
        throw new Error('Network response was not ok.');
    })
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'exported_files.db';
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
        // Reload the page after a slight delay to allow the download to initiate
        setTimeout(() => {
            window.location.reload();
        }, 1000);
    })
    .catch(error => console.error('Error exporting files:', error));
}

function startImport() {
    // Create a file input element
    let fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = '.db';  // Accept only .db files
    fileInput.onchange = e => {
        // Create a new FormData object and append the file
        let formData = new FormData();
        formData.append('db_file', e.target.files[0]);

        // Send the FormData object to the server using fetch
        fetch('/import', {
            method: 'POST',
            body: formData,
        })
        .then(response => {
            if (response.ok) {
                // Reload the page to reflect the imported data
                window.location.reload();
            } else {
                alert('Failed to import the database.');
            }
        })
        .catch(error => {
            console.error('Error importing files:', error);
            alert('Error importing files.');
        });
    };
    // Click the file input to open the file dialog
    fileInput.click();
}

