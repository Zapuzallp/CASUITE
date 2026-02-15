document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('global-search-input');
    const resultsContainer = document.getElementById('search-results-container');
    const resultsList = document.getElementById('results-list');
    let debounceTimer;

    // Open history on click/focus
    searchInput.addEventListener('focus', () => {
        renderLayout({ results: [] }, searchInput.value.trim());
    });

    searchInput.addEventListener('input', function() {
        clearTimeout(debounceTimer);
        const query = this.value.trim();

        if (query.length < 4) {
            renderLayout({ results: [] }, query);
            return;
        }

        debounceTimer = setTimeout(() => {
            fetch(`/global-search/?q=${encodeURIComponent(query)}`)
                .then(res => res.json())
                .then(data => {
                    saveToHistory(query);
                    renderLayout(data, query);
                });
        }, 300);
    });

   function highlightMatch(text, query) {
    if (!text || !query) return text || '';
    const escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const regex = new RegExp(`(${escapedQuery})`, 'gi');
    return text.toString().replace(regex, '<mark>$1</mark>');
}



    function renderLayout(data, query) {
        resultsContainer.classList.remove('d-none');
        const history = JSON.parse(localStorage.getItem('search_history') || '[]');

        // Results Column
        let resultsHtml = data.results.length > 0
            ? data.results.map(item => `
                <a href="${item.url}" class="search-card">
                    <span class="category-badge"><i class="${item.icon}"></i> ${item.type}</span>
                    <h6>${highlightMatch(item.title ?? '', query)}</h6>
                    <p class="small text-muted mb-0">
                        ${item.url}
                    </p>
                    <p class="small text-muted mb-0">
                        ${highlightMatch(item.subtitle ?? '', query)}
                    </p>
                    <p class="small text-muted mb-0">
                        ${highlightMatch(item.description ?? '', query)}
                    </p>

                </a>`).join('')
            : `<div class="p-4 text-muted">${query ? 'No results matching "' + query + '"' : 'Search'}</div>`;

        // History Column
        let historyHtml = history.map(q => `
            <div class="history-item" onclick="setSearchValue('${q}')">
                <i class="bi bi-clock-history"></i> ${q}
            </div>`).join('');

        resultsList.innerHTML = `
            <div class="search-grid">
                <div class="main-results-column">
                   <div class="section-title">
                      ${query
                        ? `Results for "${query}"`
                        : 'Quick Access'}
                   </div>

                    <div class="cards-container">${resultsHtml}</div>
                </div>
                <div class="side-column">
                    <div class="section-title">Recent Searches</div>
                    <div>${historyHtml || '<p class="small text-muted px-3">No history found</p>'}</div>
                </div>
            </div>`;
    }

    window.setSearchValue = (val) => {
        searchInput.value = val;
        searchInput.dispatchEvent(new Event('input'));
    };

    function saveToHistory(query) {
        let history = JSON.parse(localStorage.getItem('search_history') || '[]');
        history = [query, ...history.filter(i => i !== query)].slice(0, 5);
        localStorage.setItem('search_history', JSON.stringify(history));
    }

    // Close on outside click
    document.addEventListener('click', (e) => {
        if (!resultsContainer.contains(e.target) && e.target !== searchInput) {
            resultsContainer.classList.add('d-none');
        }
    });
});