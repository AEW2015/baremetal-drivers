/* Render catalog data as DOM nodes; query/catalog text is never HTML. */
(async function initializeFinder() {
    const root = document.getElementById('example-finder');
    if (!root) return;
    const query = document.getElementById('finder-query');
    const verified = document.getElementById('finder-verified');
    const family = document.getElementById('finder-family');
    const count = document.getElementById('finder-count');
    const results = document.getElementById('finder-results');
    const titles = {qemu: 'QEMU', simics: 'Simics', hardware: 'Hardware'};

    function element(tag, text, className) {
        const node = document.createElement(tag);
        if (text !== undefined) node.textContent = text;
        if (className) node.className = className;
        return node;
    }

    function link(label, href) {
        const node = element('a', label);
        const url = new URL(href, document.baseURI);
        if (!['https:', 'http:'].includes(url.protocol)) throw new Error('Invalid catalog link');
        node.href = url.href;
        return node;
    }

    try {
        const response = await fetch(new URL(root.dataset.catalogUrl, document.baseURI));
        if (!response.ok) throw new Error(`Catalog HTTP ${response.status}`);
        const {examples} = await response.json();
        for (const name of new Set(examples.map(example => example.family))) {
            const option = element('option', name);
            option.value = name;
            family.append(option);
        }
        const saved = new URL(location.href).searchParams;
        query.value = saved.get('topic') || '';
        verified.value = saved.get('verified') || 'all';
        if (!verified.value) verified.value = 'all';
        family.value = saved.get('family') || '';

        function render() {
            const matches = examples.filter(example => ExampleDiscovery.matches(example, {
                query: query.value, verified: verified.value, family: family.value,
            }));
            count.textContent = `${matches.length} of ${examples.length} examples`;
            const fragment = document.createDocumentFragment();
            for (const example of matches) {
                const card = element('article', undefined, 'finder-card');
                card.dataset.exampleId = example.id;
                card.append(element('h2', `${example.id} · ${example.title}`));
                card.append(element('p', example.family, 'finder-family'));
                const badges = element('div', undefined, 'finder-badges');
                for (const [platform, result] of Object.entries(example.platforms)) {
                    const label = `${titles[platform]}: ${result.status.toUpperCase()}`;
                    const badge = result.evidence_url ? link(label, result.evidence_url) : element('span', label);
                    badge.className = `finder-badge finder-${result.status}`;
                    badges.append(badge);
                }
                card.append(badges, element('p', example.scope));
                const links = element('nav', undefined, 'finder-links');
                links.setAttribute('aria-label', `${example.id} resources`);
                const diagram = new URL(root.dataset.diagramUrl, document.baseURI);
                diagram.searchParams.set('example', example.id);
                links.append(link('Tutorial / expected output', example.guide_url),
                    link('Source', example.source_url), link('Show in diagram', diagram.href));
                card.append(links, element('code', example.source));
                fragment.append(card);
            }
            if (!matches.length) fragment.append(element('p', 'No matches. Clear filters or try a broader topic.'));
            results.replaceChildren(fragment);
            const url = new URL(location.href);
            for (const [key, value] of [['topic', query.value], ['verified', verified.value === 'all' ? '' : verified.value], ['family', family.value]]) {
                if (value) url.searchParams.set(key, value);
                else url.searchParams.delete(key);
            }
            history.replaceState(null, '', url);
        }
        query.addEventListener('input', render);
        verified.addEventListener('change', render);
        family.addEventListener('change', render);
        document.getElementById('finder-reset').onclick = () => {
            query.value = ''; verified.value = 'all'; family.value = ''; render(); query.focus();
        };
        render();
    } catch (error) {
        count.textContent = 'Unable to load filters. Use the complete example catalog linked below.';
        console.error(error);
    }
})();
