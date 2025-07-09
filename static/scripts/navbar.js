// Toggle the filters dropdown
function toggleFiltersDropdown() {
    const dropdown = document.getElementById("filters-dropdown");
    dropdown.classList.toggle("active");
}

function fetchJobs(event) {
    event.preventDefault(); // Prevent the default form submission

    const form = event.target; // Get the form being submitted
    form.action = "/"; // Set form action explicitly to home route

    const datePosted = document.getElementById("date-posted").value; // Get the selected date posted value
    const searchQuery = document.querySelector(".searchbar").value; // Get the current search query

    // Append the search query to the form as a hidden input
    const queryInput = document.createElement("input");
    queryInput.type = "hidden";
    queryInput.name = "query";
    queryInput.value = searchQuery;
    form.appendChild(queryInput);

    // Append the date posted value to the form as a hidden input
    const datePostedInput = document.createElement("input");
    datePostedInput.type = "hidden";
    datePostedInput.name = "date_posted";
    datePostedInput.value = datePosted;
    form.appendChild(datePostedInput);

    // Append all filter values to the form as hidden inputs
    const filtersForm = document.querySelector(".filters-form");
    filtersForm.querySelectorAll("input").forEach(input => {
        if (input.checked) {
            const filterInput = document.createElement("input");
            filterInput.type = "hidden";
            filterInput.name = input.name;
            filterInput.value = input.value;
            form.appendChild(filterInput);
        }
    });

    // Submit the form
    form.submit();
}

function handleDatePostedChange(form) {
    const searchQuery = document.querySelector(".searchbar").value; // Get the current search query

    // Append the search query to the form as a hidden input
    const queryInput = document.createElement("input");
    queryInput.type = "hidden";
    queryInput.name = "query";
    queryInput.value = searchQuery;
    form.appendChild(queryInput);

    // Append all filter values to the form as hidden inputs
    const filtersForm = document.querySelector(".filters-form");
    filtersForm.querySelectorAll("input").forEach(input => {
        if (input.checked) {
            const filterInput = document.createElement("input");
            filterInput.type = "hidden";
            filterInput.name = input.name;
            filterInput.value = input.value;
            form.appendChild(filterInput);
        }
    });

    // Submit the form
    form.submit();
}