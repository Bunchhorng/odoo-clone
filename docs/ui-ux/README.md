# Workspace launcher

The Vue launcher provides links to Django Admin, the live health response, and
a short getting-started guide. Its connection badge checks both Django and MySQL
through Vite's `/api` proxy on page load and every 30 seconds. A manual refresh
button allows retrying after an outage. Connection failures show a disconnected
state, including when a request times out.

Navigation, focus states, status announcements, and small-screen layouts are
included. No company records or service statuses are hardcoded as live data.
