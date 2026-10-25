# Security boundaries

Credentials are environment-injected, provider origins fixed, HTTP redirects refused, subprocesses use argv with shell=False, and request/config credential fields are rejected. Plans bind local input/config fingerprints; dispatch locks prevent automatic replay. This does not protect against a malicious process/user with filesystem or process access, and it is not an operating-system sandbox.

Signed storage/output URLs, local reports, project account files and provider job ids may be sensitive. Keep `.commerce`, `.env` and cookies outside Git. Redaction is defense in depth, not proof any arbitrary external client output contains no secrets. Review artifacts before sharing.

Network timeout can occur after provider acceptance. Do not delete receipts/locks or automatically repeat a paid/publish request. HTTP 200 can contain a vendor business error. A platform command exiting zero is not proof of a visible post.

Report issues through https://github.com/jacksonpangc-hash/commerce-creative-skill/issues with sensitive details removed. For vulnerabilities, use a private security advisory if the repository exposes that feature; otherwise request a private reporting channel without posting exploit details, keys or private media. Do not assume private vulnerability reporting is enabled.
