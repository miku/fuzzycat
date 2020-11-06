
-- Example: Low-energy nanotube chip says 'hello world'
CREATE TABLE IF NOT EXISTS sslookup (
    id INTEGER PRIMARY KEY,
	title_prefix TEXT,
    title_suffix TEXT,
    contribs TEXT
);

CREATE INDEX idx_sslookup_title ON sslookup (title_prefix, title_suffix);
CREATE INDEX idx_sslookup_title_prefix ON sslookup (title_prefix);
CREATE INDEX idx_sslookup_title_suffix ON sslookup (title_suffix);

