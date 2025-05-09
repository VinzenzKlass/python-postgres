export default function (hljs) {
    const regex = hljs.regex
    const IDENT_RE = /[\p{XID_Start}_]\p{XID_Continue}*/u
    const RESERVED_WORDS = [
        'and',
        'as',
        'assert',
        'async',
        'await',
        'break',
        'case',
        'class',
        'continue',
        'def',
        'del',
        'elif',
        'else',
        'except',
        'finally',
        'for',
        'from',
        'global',
        'if',
        'import',
        'in',
        'is',
        'lambda',
        'match',
        'nonlocal|10',
        'not',
        'or',
        'pass',
        'raise',
        'return',
        'try',
        'while',
        'with',
        'yield',
    ]

    const BUILT_INS = [
        '__import__',
        'abs',
        'all',
        'any',
        'ascii',
        'bin',
        'bool',
        'breakpoint',
        'bytearray',
        'bytes',
        'callable',
        'chr',
        'classmethod',
        'compile',
        'complex',
        'delattr',
        'dict',
        'dir',
        'divmod',
        'enumerate',
        'eval',
        'exec',
        'filter',
        'float',
        'format',
        'frozenset',
        'getattr',
        'globals',
        'hasattr',
        'hash',
        'help',
        'hex',
        'input',
        'int',
        'isinstance',
        'issubclass',
        'iter',
        'len',
        'list',
        'locals',
        'map',
        'max',
        'memoryview',
        'min',
        'next',
        'object',
        'oct',
        'open',
        'ord',
        'pow',
        'print',
        'property',
        'range',
        'repr',
        'reversed',
        'round',
        'set',
        'setattr',
        'slice',
        'sorted',
        'staticmethod',
        'str',
        'sum',
        'super',
        'tuple',
        'type',
        'vars',
        'zip',
    ]

    const LITERALS = ['__debug__', 'Ellipsis', 'False', 'None', 'NotImplemented', 'True']
    const KEYWORDS = {
        $pattern: /(?:[A-Za-z]\w*|__\w+__)(?!=)/,
        keyword: RESERVED_WORDS,
        built_in: BUILT_INS,
        literal: LITERALS,
    }

    const PROMPT = {
        className: 'meta',
        begin: /^(>>>|\.\.\.) /,
    }

    const SUBST = {
        className: 'subst',
        begin: /\{/,
        end: /\}/,
        keywords: KEYWORDS,
        illegal: /#/,
    }

    const LITERAL_BRACKET = {
        begin: /\{\{/,
        relevance: 0,
    }

    const STRING = {
        className: 'string',
        contains: [hljs.BACKSLASH_ESCAPE],
        variants: [
            {
                begin: /([uU]|[bB]|[rR]|[bB][rR]|[rR][bB])?'''/,
                end: /'''/,
                contains: [hljs.BACKSLASH_ESCAPE, PROMPT],
                relevance: 10,
            },
            {
                begin: /([uU]|[bB]|[rR]|[bB][rR]|[rR][bB])?"""/,
                end: /"""/,
                contains: [hljs.BACKSLASH_ESCAPE, PROMPT],
                relevance: 10,
            },
            {
                begin: /([fF][rR]|[rR][fF]|[fF])'''/,
                end: /'''/,
                contains: [hljs.BACKSLASH_ESCAPE, PROMPT, LITERAL_BRACKET, SUBST],
            },
            {
                begin: /([fF][rR]|[rR][fF]|[fF])"""/,
                end: /"""/,
                contains: [hljs.BACKSLASH_ESCAPE, PROMPT, LITERAL_BRACKET, SUBST],
            },
            {
                begin: /([uU]|[rR])'/,
                end: /'/,
                relevance: 10,
            },
            {
                begin: /([uU]|[rR])"/,
                end: /"/,
                relevance: 10,
            },
            {
                begin: /([bB]|[bB][rR]|[rR][bB])'/,
                end: /'/,
            },
            {
                begin: /([bB]|[bB][rR]|[rR][bB])"/,
                end: /"/,
            },
            {
                begin: /([fF][rR]|[rR][fF]|[fF])'/,
                end: /'/,
                contains: [hljs.BACKSLASH_ESCAPE, LITERAL_BRACKET, SUBST],
            },
            {
                begin: /([fF][rR]|[rR][fF]|[fF])"/,
                end: /"/,
                contains: [hljs.BACKSLASH_ESCAPE, LITERAL_BRACKET, SUBST],
            },
            hljs.APOS_STRING_MODE,
            hljs.QUOTE_STRING_MODE,
        ],
    }

    const digitpart = '[0-9](_?[0-9])*'
    const pointfloat = `(\\b(${digitpart}))?\\.(${digitpart})|\\b(${digitpart})\\.`
    const lookahead = `\\b|${RESERVED_WORDS.join('|')}`
    const NUMBER = {
        className: 'number',
        relevance: 0,
        variants: [
            {
                begin: `(\\b(${digitpart})|(${pointfloat}))[eE][+-]?(${digitpart})[jJ]?(?=${lookahead})`,
            },
            {begin: `(${pointfloat})[jJ]?`},
            {begin: `\\b([1-9](_?[0-9])*|0+(_?0)*)[lLjJ]?(?=${lookahead})`},
            {begin: `\\b0[bB](_?[01])+[lL]?(?=${lookahead})`},
            {begin: `\\b0[oO](_?[0-7])+[lL]?(?=${lookahead})`},
            {begin: `\\b0[xX](_?[0-9a-fA-F])+[lL]?(?=${lookahead})`},
            {begin: `\\b(${digitpart})[jJ](?=${lookahead}) `},
        ],
    }
    const COMMENT_TYPE = {
        className: 'comment',
        begin: regex.lookahead(/# type:/),
        end: /$/,
        keywords: KEYWORDS,
        contains: [
            {
                // prevent keywords from coloring `type`
                begin: /# type:/,
            }, // comment within a datatype comment includes no keywords
            {
                begin: /#/,
                end: /\b\B/,
                endsWithParent: true,
            },
        ],
    }
    const PARAMS = {
        className: 'params',
        variants: [
            {
                className: '',
                begin: /\(\s*\)/,
                skip: true,
            },
            {
                begin: /\(/,
                end: /\)/,
                excludeBegin: true,
                excludeEnd: true,
                keywords: KEYWORDS,
                contains: ['self', PROMPT, NUMBER, STRING, hljs.HASH_COMMENT_MODE],
            },
        ],
    }
    SUBST.contains = [STRING, NUMBER, PROMPT]

    const PG_KW = 'ABORT ALTER ANALYZE BEGIN CALL CHECKPOINT|10 CLOSE CLUSTER COMMENT COMMIT COPY CREATE DEALLOCATE DECLARE '
        + 'DELETE DISCARD DO DROP END EXECUTE EXPLAIN FETCH GRANT IMPORT INSERT LISTEN LOAD LOCK MOVE NOTIFY '
        + 'PREPARE REASSIGN|10 REFRESH REINDEX RELEASE RESET REVOKE ROLLBACK SAVEPOINT SECURITY SELECT SET SHOW '
        + 'START TRUNCATE UNLISTEN|10 UPDATE VACUUM|10 VALUES '
        + 'AGGREGATE COLLATION CONVERSION|10 DATABASE DEFAULT PRIVILEGES DOMAIN TRIGGER EXTENSION FOREIGN '
        + 'WRAPPER|10 TABLE FUNCTION GROUP LANGUAGE LARGE OBJECT MATERIALIZED VIEW OPERATOR CLASS '
        + 'FAMILY POLICY PUBLICATION|10 ROLE RULE SCHEMA SEQUENCE SERVER STATISTICS SUBSCRIPTION SYSTEM '
        + 'TABLESPACE CONFIGURATION DICTIONARY PARSER TEMPLATE TYPE USER MAPPING PREPARED ACCESS '
        + 'METHOD CAST AS TRANSFORM TRANSACTION OWNED TO INTO SESSION AUTHORIZATION '
        + 'INDEX PROCEDURE ASSERTION '
        + 'ALL ANALYSE AND ANY ARRAY ASC ASYMMETRIC|10 BOTH CASE CHECK '
        + 'COLLATE COLUMN CONCURRENTLY|10 CONSTRAINT CROSS '
        + 'DEFERRABLE RANGE '
        + 'DESC DISTINCT ELSE EXCEPT FOR FREEZE|10 FROM FULL HAVING '
        + 'ILIKE IN INITIALLY INNER INTERSECT IS ISNULL JOIN LATERAL LEADING LIKE LIMIT '
        + 'NATURAL NOT NOTNULL NULL OFFSET ON ONLY ORDER OR OUTER OVERLAPS PLACING PRIMARY '
        + 'REFERENCES RETURNING SIMILAR SOME SYMMETRIC TABLESAMPLE THEN '
        + 'TRAILING UNION UNIQUE USING VARIADIC|10 VERBOSE WHEN WHERE WINDOW WITH '
        + 'BY RETURNS INOUT OUT SETOF|10 IF STRICT CURRENT CONTINUE OWNER LOCATION OVER PARTITION WITHIN '
        + 'BETWEEN ESCAPE EXTERNAL INVOKER DEFINER WORK RENAME VERSION CONNECTION CONNECT '
        + 'TABLES TEMP TEMPORARY FUNCTIONS SEQUENCES TYPES SCHEMAS OPTION CASCADE RESTRICT ADD ADMIN '
        + 'EXISTS VALID VALIDATE ENABLE DISABLE REPLICA|10 ALWAYS PASSING COLUMNS PATH '
        + 'REF VALUE OVERRIDING IMMUTABLE STABLE VOLATILE BEFORE AFTER EACH ROW PROCEDURAL '
        + 'ROUTINE NO HANDLER VALIDATOR OPTIONS STORAGE OIDS|10 WITHOUT INHERIT DEPENDS CALLED '
        + 'INPUT LEAKPROOF|10 COST ROWS NOWAIT SEARCH UNTIL ENCRYPTED|10 PASSWORD CONFLICT|10 '
        + 'INSTEAD INHERITS CHARACTERISTICS WRITE CURSOR ALSO STATEMENT SHARE EXCLUSIVE INLINE '
        + 'ISOLATION REPEATABLE READ COMMITTED SERIALIZABLE UNCOMMITTED LOCAL GLOBAL SQL PROCEDURES '
        + 'RECURSIVE SNAPSHOT ROLLUP CUBE TRUSTED|10 INCLUDE FOLLOWING PRECEDING UNBOUNDED RANGE GROUPS '
        + 'UNENCRYPTED|10 SYSID FORMAT DELIMITER HEADER QUOTE ENCODING FILTER OFF '
        + 'FORCE_QUOTE FORCE_NOT_NULL FORCE_NULL COSTS BUFFERS TIMING SUMMARY DISABLE_PAGE_SKIPPING '
        + 'RESTART CYCLE GENERATED IDENTITY DEFERRED IMMEDIATE LEVEL LOGGED UNLOGGED '
        + 'OF NOTHING NONE EXCLUDE ATTRIBUTE '
        + 'USAGE ROUTINES '
        + 'TRUE FALSE NAN INFINITY KEY vector';

    return {
        name: 'Python',
        aliases: ['py', 'gyp', 'ipython'],
        unicodeRegex: true,
        keywords: KEYWORDS,
        illegal: /(<\/|\?)|=>/,
        contains: [
            PROMPT,
            NUMBER,
            {
                scope: 'variable.language',
                match: /\bself\b/,
            },
            {
                beginKeywords: 'if',
                relevance: 0,
            },
            {match: /\bor\b/, scope: 'keyword'},
            COMMENT_TYPE,
            hljs.HASH_COMMENT_MODE,
            {
                match: [/\bdef/, /\s+/, IDENT_RE],
                scope: {
                    1: 'keyword',
                    3: 'title.function',
                },
                contains: [PARAMS],
            },
            {
                variants: [
                    {
                        match: [/\bclass/, /\s+/, IDENT_RE, /\s*/, /\(\s*/, IDENT_RE, /\s*\)/],
                    },
                    {
                        match: [/\bclass/, /\s+/, IDENT_RE],
                    },
                ],
                scope: {
                    1: 'keyword',
                    3: 'title.class',
                    6: 'title.class.inherited',
                },
            },
            {
                className: 'meta',
                begin: /^[\t ]*@/,
                end: /(?=#)|$/,
                contains: [NUMBER, PARAMS, STRING],
            },
            {
                match: /\b(?![TFN](?:rue|alse|one)\b)(?:[A-Z][a-zA-Z0-9]*|_[A-Z][a-zA-Z0-9]*)\b(?!\s*\()/,
                scope: 'type',
            },
            {
                match: [/\./, IDENT_RE, /\s*\(/],
                scope: {
                    2: 'title.function',
                },
            },
            {
                match: [/([A-Z][a-zA-Z0-9_]*)/, /\s*\(/],
                scope: {
                    1: 'title.function',
                },
            },
            {
                match: [
                    new RegExp(
                        `\\b(?!(?:${BUILT_INS.map((name) => name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join(
                            '|'
                        )})(?=\\s*\\())([\\p{XID_Start}_][\\p{XID_Continue}]*)`,
                        'u'
                    ),
                    /\s*\(/,
                ],
                scope: {
                    1: 'title.function',
                },
            },
            {
                className: 'string',
                begin: /(["'])(\s*)(?=SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|TRUNCATE)\b/i,
                end: /(["'])/,
                contains: [
                    {
                        className: 'keyword',
                        match: PG_KW.trim().replace(/ /g, '|'),
                    },
                    {
                        className: 'type',
                        begin: /%s/,
                    },
                    {
                        className: 'sql-text',
                        match: /[;*,+_a-z<>\-=]|\(|\)/,
                    },
                    {
                        className: 'number',
                        match: /\b\d+\b/,
                    }
                ]
            },
            STRING,
        ],
    }
}
