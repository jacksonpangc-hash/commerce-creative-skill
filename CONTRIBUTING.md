# Contributing

Use a dedicated branch and Python 3.10+. Start with a failing offline test for behavior changes, implement the smallest fix and run the suite. Test provider-native response shapes, interrupted streams, missing credentials, input mutation, two-step confirmation and replay prevention. Do not turn recorded examples into claims of live acceptance.

Do not add keys, cookies, personal media, populated environment files or private endpoint dumps. New providers need primary documentation, capability/authorization limits, injected-transport tests, examples and user-visible state semantics. Retain unsupported features as explicit gaps rather than successful stubs.

Run `PYTHONPATH=skills/commerce-creative/scripts python3 -m unittest discover -s tests -v`, build the wheel/source distribution, and inspect source-only archives. Contributions to original integration code are under MIT. Changes do not authorize uploading samples, paid testing, posting, purchases, pushes or releases.
