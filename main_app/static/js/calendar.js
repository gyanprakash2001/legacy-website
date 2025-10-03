// calendar.js (Handles all event/filter data and calendar rendering)

let currentDate = new Date();
window.currentEventDates = {};

/// calendar.js

// GLOBAL FUNCTION: Collects filter parameters from the modal
function getFilterParams() {
    const params = new URLSearchParams();

    // References to filter inputs from the modal (ID's found in dashboard.html)
    const eventTypeFilter = document.getElementById('event-category-filter');
    const feesFilter = document.getElementById('event-fees-filter');
    const myCollegeFilter = document.getElementById('my-college-filter');
    const appliedFilter = document.getElementById('applied-filter');

    // NEW REFERENCE: Read the clean, selected state name from the hidden input
    const selectedStateHiddenInput = document.getElementById('selected-state-name');

    // Value retrieval
    const eventTypeId = eventTypeFilter ? eventTypeFilter.value : '';
    const fees = feesFilter ? feesFilter.value : '';
    const myCollegeOnly = myCollegeFilter ? myCollegeFilter.checked : false;
    const applied = appliedFilter ? appliedFilter.checked : false;

    // NEW VALUE: Read from the hidden input
    const stateFilterName = selectedStateHiddenInput ? selectedStateHiddenInput.value.trim() : '';

    // Parameter appending
    if (eventTypeId) params.append('event_type', eventTypeId);
    if (fees) params.append('fees', fees);
    if (myCollegeOnly) params.append('my_college_only', 'true');
    if (applied) params.append('applied_filter', 'true');

    // ADD NEW FILTER TO THE API CALL
    if (stateFilterName) params.append('state', stateFilterName); // API view will filter by 'state'

    return params.toString();
}


// GLOBAL FUNCTION: Handles the filter API call and re-renders the calendar
window.fetchEventDates = async () => {
    const params = getFilterParams();
    try {
        const response = await fetch(`/calendar-events-api/?${params}`);
        const data = await response.json();

        window.currentEventDates = data.events_by_date;
        window.renderCalendar();
    } catch (error) {
        console.error('Error fetching filtered event dates:', error);
        window.currentEventDates = {};
        window.renderCalendar();
    }
};

// GLOBAL FUNCTION: Logic for applying filters (called by the modal button in main.js)
function applyFilters() {
    window.fetchEventDates();
}


document.addEventListener('DOMContentLoaded', function() {
    // --- Element References ---
    const calendarGrid = document.getElementById('calendar-grid');
    const currentMonthDisplay = document.getElementById('current-month');
    const prevMonthBtn = document.getElementById('prev-month');
    const nextMonthBtn = document.getElementById('next-month');

    // Renders the daily events in the modal after a calendar day click
    const renderDailyEvents = (dateString, events) => {
        const modal = document.getElementById('daily-event-modal');
        const modalDate = document.getElementById('modal-date');
        const eventList = document.getElementById('daily-event-list');

        modalDate.textContent = dateString;
        eventList.innerHTML = '';

        events.forEach(event => {
            const eventDiv = document.createElement('div');
            eventDiv.classList.add('daily-event-item');

            const link = document.createElement('a');
            link.href = `/apply/${event.link_key}/`;
            link.textContent = `${event.type_name} - ${event.location}: ${event.name} (${event.date_time.slice(11)})`;

            eventDiv.appendChild(link);
            eventList.appendChild(eventDiv);
        });

        modal.style.display = 'block';
    };

    // Calendar rendering logic (made accessible globally via window)
    window.renderCalendar = () => {
        const year = currentDate.getFullYear();
        const month = currentDate.getMonth();
        const today = new Date();

        currentMonthDisplay.textContent = new Date(year, month).toLocaleString('default', { month: 'long', year: 'numeric' });
        calendarGrid.innerHTML = '';

        const firstDayOfMonth = new Date(year, month, 1).getDay();
        const startDayIndex = firstDayOfMonth;

        for (let i = 0; i < startDayIndex; i++) {
            const emptyDay = document.createElement('div');
            emptyDay.classList.add('calendar-day', 'inactive');
            calendarGrid.appendChild(emptyDay);
        }

        const lastDayOfMonth = new Date(year, month + 1, 0).getDate();
        const filtersActive = getFilterParams() !== '';

        for (let i = 1; i <= lastDayOfMonth; i++) {
            const day = document.createElement('div');
            day.classList.add('calendar-day');
            day.textContent = i;

            const dateString = `${year}-${String(month + 1).padStart(2, '0')}-${String(i).padStart(2, '0')}`;

            if (i === today.getDate() && month === today.getMonth() && year === today.getFullYear()) {
                day.classList.add('today');
            }

            const eventsOnDay = window.currentEventDates[dateString];

            if (eventsOnDay && eventsOnDay.length > 0) {
                if (filtersActive) {
                    day.classList.add('filtered-event-day'); // Pink highlight
                } else {
                    day.classList.add('event-day'); // Normal highlight
                }
                day.dataset.dateString = dateString;
            }

            calendarGrid.appendChild(day);
        }
    };

    // --- Event Listeners ---

    // Calendar Navigation
    prevMonthBtn.addEventListener('click', () => {
        currentDate.setMonth(currentDate.getMonth() - 1);
        window.fetchEventDates();
    });

    nextMonthBtn.addEventListener('click', () => {
        currentDate.setMonth(currentDate.getMonth() + 1);
        window.fetchEventDates();
    });

    // Calendar Day Click (opens daily events modal)
    calendarGrid.addEventListener('click', (e) => {
        const targetDay = e.target.closest('.event-day, .filtered-event-day');
        if (targetDay) {
            const dateString = targetDay.dataset.dateString;
            const eventsOnDay = window.currentEventDates[dateString];

            if (eventsOnDay && eventsOnDay.length > 0) {
                renderDailyEvents(dateString, eventsOnDay);
            } else {
                window.location.href = `/events/create/`;
            }
        }
    });

    // Daily Event Modal Close
    document.querySelector('.close-daily-modal-btn').addEventListener('click', () => {
        document.getElementById('daily-event-modal').style.display = 'none';
    });

    window.addEventListener('click', (event) => {
        const modal = document.getElementById('daily-event-modal');
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });

    // Initial load: Fetch events
    window.fetchEventDates();
});