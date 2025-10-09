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

    // --- 3. FILTER MODAL LOGIC (Correct) ---
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


    // --- 4. STATE AUTOCOMPLETE LOGIC FOR EVENT FILTER MODAL (Correct) ---
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


    // =========================================================
    // --- 5. NEW: MEDIA MODAL/GALLERY LOGIC (THE FIX) ---
    // =========================================================
    const modal = document.getElementById('media-modal');
    const close = modal.querySelector('.close-btn');
    const modalImage = document.getElementById('modal-image');
    const modalVideo = document.getElementById('modal-video');
    const prevMediaBtn = document.getElementById('prev-media');
    const nextMediaBtn = document.getElementById('next-media');

    let currentMediaUrls = [];
    let currentIndex = 0;

    // Helper function to show the current media item
    const showCurrentMedia = () => {
        const url = currentMediaUrls[currentIndex];
        const isVideo = url.toLowerCase().endsWith('.mp4') || url.toLowerCase().endsWith('.webm');

        // Reset visibility
        modalImage.style.display = 'none';
        modalVideo.style.display = 'none';

        if (isVideo) {
            modalVideo.src = url;
            modalVideo.style.display = 'block';
            modalVideo.load();
        } else {
            modalImage.src = url;
            modalImage.style.display = 'block';
        }

        // Hide navigation buttons if there is only one item
        if (currentMediaUrls.length <= 1) {
            prevMediaBtn.style.display = 'none';
            nextMediaBtn.style.display = 'none';
        } else {
            prevMediaBtn.style.display = 'block';
            nextMediaBtn.style.display = 'block';
        }
    };

    // 5.1. Open Modal on Media Click
    document.querySelectorAll('.media-gallery').forEach(gallery => {
        gallery.addEventListener('click', (e) => {
            const clickedItem = e.target.closest('.gallery-item, .gallery-plus-sign');

            if (clickedItem) {
                const mediaUrlsString = gallery.dataset.mediaUrls;
                if (!mediaUrlsString) return;

                // Safely parse the JSON string from the data attribute
                try {
                    currentMediaUrls = JSON.parse(mediaUrlsString);
                } catch (error) {
                    console.error('Error parsing media URLs:', error);
                    return;
                }

                // Determine the index of the clicked item (if it's one of the visible ones)
                if (e.target.closest('.gallery-item')) {
                    const galleryItems = gallery.querySelectorAll('.gallery-item');
                    currentIndex = Array.from(galleryItems).indexOf(e.target.closest('.gallery-item'));
                    // If the click was on the plus sign, just open to the first one (index 0)
                } else if (e.target.closest('.gallery-plus-sign')) {
                     currentIndex = 0; // Start at the beginning for plus sign click
                }

                // Fallback to 0 if we somehow clicked something else or index is out of bounds
                if (currentIndex === -1) currentIndex = 0;


                showCurrentMedia();
                modal.style.display = 'flex'; // Use flex to help with centering modal content
            }
        });
    });

    // 5.2. Close Modal
    close.onclick = function() {
        modal.style.display = 'none';
        modalVideo.pause(); // Stop video playback when closing
    }

    // Close modal if user clicks outside of the content container
    window.addEventListener('click', (event) => {
        if (event.target === modal) {
            modal.style.display = 'none';
            modalVideo.pause();
        }
    });

    // 5.3. Navigation (Previous)
    prevMediaBtn.addEventListener('click', (e) => {
        e.stopPropagation(); // Prevent the click from bubbling up to close the modal
        currentIndex = (currentIndex > 0) ? currentIndex - 1 : currentMediaUrls.length - 1;
        showCurrentMedia();
    });

    // 5.4. Navigation (Next)
    nextMediaBtn.addEventListener('click', (e) => {
        e.stopPropagation(); // Prevent the click from bubbling up to close the modal
        currentIndex = (currentIndex < currentMediaUrls.length - 1) ? currentIndex + 1 : 0;
        showCurrentMedia();
    });
});