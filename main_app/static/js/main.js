// main.js

document.addEventListener('DOMContentLoaded', function() {

    // --- UTILITY/AUTH (Correct) ---
    function getCookie(name) {
        // ... (CSRF logic) ...
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // --- SETUP HOVER (Correct) ---
    const setupQueryHover = () => {
        const queryContainers = document.querySelectorAll('.query-container');
        queryContainers.forEach(container => {
            const popup = container.querySelector('.contact-info-popup');
            const phoneInfo = container.querySelector('.phone-info');
            const showPhone = container.dataset.showPhone === 'true';

            container.addEventListener('mouseenter', () => {
                if (showPhone && phoneInfo) {
                    phoneInfo.style.display = 'block';
                }
                if (popup) popup.style.display = 'block';
            });

            container.addEventListener('mouseleave', () => {
                if (popup) popup.style.display = 'none';
                if (phoneInfo) phoneInfo.style.display = 'none';
            });
        });
    };
    setupQueryHover();

    // --- 1. College Follow/Unfollow Logic (Correct) ---
    const collegeList = document.getElementById('suggestedCollegeList');
    if (collegeList) {
        collegeList.addEventListener('click', function(event) {
            const followBtn = event.target.closest('.follow-btn');
            if (followBtn) {
                event.preventDefault();
                const collegeName = followBtn.getAttribute('data-college-name');
                const isFollowing = followBtn.classList.contains('following');
                const actionUrl = '/community/toggle-follow/';
                const formData = new FormData();
                formData.append('college_name', collegeName);
                formData.append('action', isFollowing ? 'unfollow' : 'follow');
                formData.append('csrfmiddlewaretoken', getCookie('csrftoken'));

                fetch(actionUrl, { method: 'POST', body: formData })
                .then(response => {
                    if (!response.ok) throw new Error('Server error or network issue');
                    return response.json();
                })
                .then(data => {
                    if (data.status === 'followed') {
                        followBtn.textContent = 'Following';
                        followBtn.classList.add('following');
                    } else if (data.status === 'unfollowed') {
                        followBtn.textContent = 'Follow';
                        followBtn.classList.remove('following');
                    } else {
                        alert('Error: Could not update follow status.');
                    }
                })
                .catch(error => {
                    console.error('Fetch error:', error);
                    alert('An error occurred. Please check the network and try again.');
                });
            }
        });
    }

    // --- 2. College Autocomplete Search Logic (Correct) ---
    const searchInput = document.getElementById('collegeSearchInput');
    const searchContainer = document.querySelector('.college-search-container');
    let dropdown = null;

    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const query = searchInput.value.trim();

            if (dropdown) {
                dropdown.remove();
                dropdown = null;
            }

            if (query.length > 2) {
                const autocompleteUrl = "/college-autocomplete/?q=" + encodeURIComponent(query);

                fetch(autocompleteUrl)
                    .then(response => response.json())
                    .then(data => {
                        if (data.length > 0) {
                            dropdown = document.createElement('ul');
                            dropdown.classList.add('autocomplete-dropdown');

                            data.forEach(college => {
                                const listItem = document.createElement('li');
                                const collegeLink = document.createElement('a');
                                const encodedName = encodeURIComponent(college.name);

                                collegeLink.href = `/community/${encodedName}/`;
                                collegeLink.textContent = college.name;

                                listItem.appendChild(collegeLink);
                                dropdown.appendChild(listItem);
                            });
                            searchContainer.appendChild(dropdown);
                        }
                    })
                    .catch(error => console.error('Error fetching autocomplete data:', error));
            }
        });

        document.addEventListener('click', function(event) {
            if (dropdown && !searchContainer.contains(event.target) && !dropdown.contains(event.target)) {
                 dropdown.remove();
                 dropdown = null;
            }
        });
    }

    // --- 3. NEW FILTER MODAL LOGIC (Correct) ---
    const filterTrigger = document.getElementById('eventFilterTrigger');
    const filterModal = document.getElementById('filterModal');
    const closeBtn = document.getElementById('closeFilterModal');
    const applyBtn = document.getElementById('apply-filters-btn');

    // 3.1. Open the modal when the trigger is clicked
    if (filterTrigger) {
        filterTrigger.addEventListener('click', function() {
            filterModal.style.display = "block";
        });
    }

    // 3.2. Close the modal when the 'x' is clicked
    if (closeBtn) {
        closeBtn.onclick = function() {
            filterModal.style.display = "none";
        }
    }

    // 3.3. Close the modal if the user clicks outside of it
    window.addEventListener('click', (event) => {
        if (event.target === filterModal) {
            filterModal.style.display = "none";
        }
    });

    // 3.4. Run filter logic (from calendar.js) and close modal when APPLY button is clicked
    if (applyBtn) {
        applyBtn.addEventListener('click', function() {
            if (typeof applyFilters === 'function') {
                applyFilters();
            } else {
                 console.error("applyFilters function is not defined. Ensure calendar.js is loaded first.");
            }
            filterModal.style.display = "none";
        });
    }


    // --- 4. STATE AUTOCOMPLETE LOGIC FOR EVENT FILTER MODAL (MOVED HERE) ---
    const stateInput = document.getElementById('state-filter-input');
    const selectedStateHiddenInput = document.getElementById('selected-state-name');
    let stateDropdown = null;

    if (stateInput) {
        stateInput.addEventListener('input', function() {
            const query = stateInput.value.trim();

            if (stateDropdown) {
                stateDropdown.remove();
                stateDropdown = null;
            }

            selectedStateHiddenInput.value = '';

            if (query.length > 1) { // Start search after 1 character
                const autocompleteUrl = "/api/state-autocomplete/?q=" + encodeURIComponent(query);

                fetch(autocompleteUrl)
                    .then(response => response.json())
                    .then(data => {
                        if (data.length > 0) {
                            stateDropdown = document.createElement('ul');
                            stateDropdown.classList.add('autocomplete-dropdown');

                            // --- Positioning logic ---
                            stateDropdown.style.position = 'absolute';
                            stateDropdown.style.zIndex = '1001';

                            const inputRect = stateInput.getBoundingClientRect();
                            stateDropdown.style.top = `${inputRect.bottom + window.scrollY}px`;
                            stateDropdown.style.left = `${inputRect.left}px`;
                            stateDropdown.style.width = `${inputRect.width}px`;
                            // --- End Positioning logic ---

                            data.forEach(item => {
                                const listItem = document.createElement('li');
                                listItem.textContent = item.state_name;
                                listItem.addEventListener('click', () => {
                                    stateInput.value = item.state_name;
                                    selectedStateHiddenInput.value = item.state_name;
                                    stateDropdown.remove();
                                    stateDropdown = null;
                                });
                                stateDropdown.appendChild(listItem);
                            });

                            document.body.appendChild(stateDropdown);
                        }
                    })
                    .catch(error => console.error('Error fetching state data:', error));
            }
        });

        // Hide dropdown when clicking elsewhere
        document.addEventListener('click', function(event) {
            if (stateDropdown && !stateInput.contains(event.target) && !stateDropdown.contains(event.target)) {
                 stateDropdown.remove();
                 stateDropdown = null;
            }
        });
    }

});