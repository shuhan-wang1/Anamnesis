/* KaTeX initialization and math rendering */

let KATEX_MACROS = {};

async function initKaTeX() {
    try {
        const macros = await API.getMacros();
        KATEX_MACROS = {};
        for (const [name, expansion] of Object.entries(macros)) {
            KATEX_MACROS[name] = expansion;
        }
        // Add common macros not in the source files
        KATEX_MACROS['\\mathbb'] = KATEX_MACROS['\\mathbb'] || undefined; // native
        KATEX_MACROS['\\mathcal'] = KATEX_MACROS['\\mathcal'] || undefined; // native
        console.log(`Loaded ${Object.keys(macros).length} KaTeX macros`);
    } catch (e) {
        console.warn('Could not load macros:', e);
    }
}

function renderMath(element) {
    if (!element) return;
    try {
        renderMathInElement(element, {
            delimiters: [
                { left: '$$', right: '$$', display: true },
                { left: '$', right: '$', display: false },
                { left: '\\[', right: '\\]', display: true },
                { left: '\\(', right: '\\)', display: false },
            ],
            macros: KATEX_MACROS,
            throwOnError: false,
            trust: true,
        });
    } catch (e) {
        console.warn('KaTeX render error:', e);
    }
}

function renderMathContent(container, content) {
    container.innerHTML = content;
    renderMath(container);
}
