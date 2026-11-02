/* Shared by the website finder and the standalone, offline diagram. */
window.ExampleDiscovery = (() => {
    const targets = {
        all: [], qemu: ['qemu'], simics: ['simics'], hardware: ['hardware'],
        both: ['simics', 'hardware'], 'all-three': ['qemu', 'simics', 'hardware'],
    };

    function matches(example, {query = '', verified = 'all', family = ''} = {}) {
        const required = targets[verified];
        if (!required || (family && example.family !== family)) return false;
        // Partial, reference and build-only outcomes are never promoted to PASS.
        if (!required.every(platform => example.platforms[platform].status === 'pass')) return false;
        const searchable = [example.id, example.title, example.family, example.scope,
            ...(example.blocks || [])].join(' ').toLowerCase();
        return query.toLowerCase().trim().split(/\s+/).every(term => searchable.includes(term));
    }

    return {matches, targets};
})();
