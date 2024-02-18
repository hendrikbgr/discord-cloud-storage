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
        tdId = tr[i].getElementsByTagName('td')[0];
        // Get the second cell (File Name)
        tdName = tr[i].getElementsByTagName('td')[1];

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

