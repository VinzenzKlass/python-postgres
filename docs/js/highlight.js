document$.subscribe(() => {
    Promise.all([import('./assets/hljs.min.js'), import('./assets/python.min.js'), import('./assets/psql.min.js')]).then(([hljsModule, pyModule, pslqModule]) => {
        const hljs = hljsModule.default
        const python = pyModule.default
        const psql = pslqModule.default
        hljs.configure({languages: ['python', 'pgsql'], ignoreUnescapedHTML: true})
        hljs.registerLanguage('python', python)
        hljs.registerLanguage('pgsql', psql)
        hljs.highlightAll()
    })
})
