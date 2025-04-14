// Initialize charts when document is ready
$(document).ready(function() {
    // Fetch dashboard data
    $.ajax({
        url: '/get_dashboard_data/',
        method: 'GET',
        success: function(response) {
            if (response.success) {
                updateDashboard(response.data);
            } else {
                console.error('Failed to fetch dashboard data:', response.error);
            }
        },
        error: function(xhr, status, error) {
            console.error('Error fetching dashboard data:', error);
        }
    });
});

// Update dashboard with data
function updateDashboard(data) {
    // Update overview stats
    updateOverviewStats(data.overview);
    
    // Initialize charts
    initializeStatusChart(data.status_distribution);
    initializeApplicationsChart(data.applications_over_time);
    initializeSkillChart(data.skill_distribution);
    initializeSourcesChart(data.application_sources);
    
    // Update recent activity
    updateRecentActivity(data.recent_activity);
    
    // Update top jobs
    updateTopJobs(data.top_jobs);
}

// Update overview statistics
function updateOverviewStats(stats) {
    $('#total-applications').text(stats.active_applications);
    $('#active-jobs').text(stats.total_jobs);
    $('#new-applications').text(stats.pending_reviews);
    $('#shortlisted').text(stats.shortlisted_candidates);
}

// Initialize status distribution chart
function initializeStatusChart(data) {
    const ctx = document.getElementById('statusChart').getContext('2d');
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.labels,
            datasets: [{
                data: data.values,
                backgroundColor: [
                    '#007bff',
                    '#28a745',
                    '#ffc107',
                    '#dc3545',
                    '#6c757d'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false
        }
    });
}

// Initialize applications over time chart
function initializeApplicationsChart(data) {
    const ctx = document.getElementById('applicationsChart').getContext('2d');
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.dates,
            datasets: [{
                label: 'Applications',
                data: data.values,
                borderColor: '#007bff',
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

// Initialize skill distribution chart
function initializeSkillChart(data) {
    const ctx = document.getElementById('skillChart').getContext('2d');
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels,
            datasets: [{
                label: 'Skill Distribution',
                data: data.values,
                backgroundColor: '#007bff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

// Initialize application sources chart
function initializeSourcesChart(data) {
    const ctx = document.getElementById('sourcesChart').getContext('2d');
    new Chart(ctx, {
        type: 'pie',
        data: {
            labels: data.labels,
            datasets: [{
                data: data.values,
                backgroundColor: [
                    '#007bff',
                    '#28a745',
                    '#ffc107',
                    '#dc3545'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false
        }
    });
}

// Update recent activity table
function updateRecentActivity(activities) {
    const tbody = $('#recentActivity tbody');
    tbody.empty();
    
    activities.forEach(activity => {
        tbody.append(`
            <tr>
                <td>${activity.description}</td>
                <td>${activity.title}</td>
                <td>${activity.type}</td>
                <td>${new Date(activity.timestamp).toLocaleDateString()}</td>
            </tr>
        `);
    });
}

// Update top jobs table
function updateTopJobs(jobs) {
    const tbody = $('#topJobs tbody');
    tbody.empty();
    
    jobs.forEach(job => {
        tbody.append(`
            <tr>
                <td>${job.title}</td>
                <td>${job.applications}</td>
                <td><span class="badge badge-${job.status === 'active' ? 'success' : 'danger'}">${job.status}</span></td>
            </tr>
        `);
    });
} 