# Style Guide

## Purpose

This document is a style guide for Python code in this project. It is read by LLMs generating or modifying code in the repo.

The rules here are not a complete Python style guide; universally-followed conventions (PEP 8, snake_case, module-level loggers, standard level semantics) are assumed and not restated. What follows is specifically the set of conventions that LLMs don't follow by default; rules that override common LLM defaults or encode project-specific decisions. Prefer automated tooling to style guides whenever possible; rules here exist because tooling can't enforce them.

Apply these rules when writing new code and when modifying existing code. When a rule and existing code conflict, update the existing code to match the rule unless doing so is out of scope for the current task. Limit changes to what's necessary to apply the rule; don't rewrite adjacent code beyond what was asked.

If a rule conflicts with an explicit instruction in the current prompt, the prompt wins for that task, but flag the conflict in the response so the style guide can be updated if needed.

## Tools

Tools that run against this codebase. Don't restate conventions these already enforce.

- uv
- pre-commit
- ruff-check
- ruff-format
- pyright
- typos
- mdformat
- pytest

## Style

- Don't use em dashes anywhere; use semicolons, commas, or two sentences
- Multi-line strings require explicit `+` between fragments; implicit adjacent-literal concatenation is banned by the linter

## Naming

- Put more generic terms nearer the start of an identifier, more specific as you move right.
  - Files: `parser_yaml.py`, `parser_json.py`
  - Classes: `ParserYaml`, `ParserJson`
  - Functions: `parse_yaml`, `parse_json`
- Don't uppercase abbreviations, even common ones (prefer ParserJson to ParserJSON)

## Imports

- Imports go at the top of the file; don't inline imports inside functions to avoid circular dependencies; fix the dependency structure instead

## CLI tool invocation

- When invoking CLI tools from Python, prefer long-form subcommands over short aliases for readability (e.g., `apktool install-framework` over `apktool if`)

## Comments

- Don't use banner comments (ASCII borders, section delineators)
- When refactoring, don't explain the reason for the refactor in the comment; the comment describes the code, not its history

## Logging

- Don't use f-strings in log calls; f-strings evaluate at call time even when the log level is disabled. Use `%s`-style format strings with separate arguments: `logger.info("found %d files in %s", n, path)`
- Logging is for observability; exceptions are for control flow. Don't log and raise for the same event; the caller's `logger.exception` catches the detail
- Log at the layer that has the relevant context; a deep utility function usually shouldn't log, because it doesn't know whether its caller is in a noisy batch job or a quiet script
- Library code may call `logger.info` / `logger.warning` / etc. on its module-level logger, but must not configure handlers, call `logging.basicConfig`, or otherwise install logging infrastructure; that's the consuming application's job
- When logging about a file, directory, or path, include the path in the log message; "extracted archive" is useless for debugging, "extracted archive to /path/to/dest" is not
- Log messages should include the specific values they're about: paths, URLs, IDs, counts, command args. A message that says only what happened without saying what it happened to is rarely useful for debugging

## Log message format

- Values (paths, IDs, counts) appear unquoted in context unless quoting prevents ambiguity
- Use a colon for labeled values: `exit code: 1`, `output directory: /tmp/foo`
- One sentence per log line; split multi-part information into multiple log calls
- Include units on numbers when the unit isn't obvious (`0.3s`, `1024 bytes`)
- Error messages describe the condition as a statement, not as a command to the reader

## Docstrings

- Use Google-style docstring sections when they add information; omit them when they would only restate the signature
- Only `Args:`, `Returns:`/`Yields:`, and `Raises:` sections are permitted; other Google-style sections should be written as prose in the body of the docstring
- Do NOT use reStructuredText/Sphinx field syntax (`:param:`, `:returns:`, `:raises:`)
- Do NOT use NumPy-style underlined headings
- A docstring without any sections is fine and often preferable; don't add sections for their own sake
- Within a section, document only the entries that need explanation; partial coverage is better than padded coverage
- Keep docstrings short; if you find yourself writing a paragraph per parameter, the docstring is doing too much
- Don't treat `Raises:` as exhaustive; only list exceptions callers are meant to catch programmatically
- Don't list a single domain exception in `Raises:` if the exception class is defined at module scope nearby
- For parameters that map directly to external tool flags or APIs, lead with the mechanical mapping before the semantic explanation
- When writing a docstring in response to a prompt, write it for a reader who hasn't seen the prompt; don't restate the instructions you were given or describe implementation mechanics the prompt specified

## Exceptions

- Exceptions are for "I cannot proceed"; use logging for warnings or recoverable conditions
- Default to one-line, flat `Exception` subclasses with no `__init__`, no attributes, and no hierarchy
- Add attributes to an exception only when callers actually read them programmatically; the presence of an attribute is a commitment that it's part of the public API
- Library-boundary exceptions (from reusable packages consumed by other code) may carry structured data callers need to inspect; pipeline- and application-level exceptions should default to the flat form
- When you do deviate from the flat form, encode domain information in the message, not in subclass structure
- Let stdlib exceptions propagate freely from primitive operations; don't wrap them
- Raise your own domain exception at the point of detection, not a stdlib exception to be caught and re-raised elsewhere
- Catch locally only when you have a specific per-failure plan (retry, fallback, aggregate, skip)
- When trying multiple alternatives, aggregate errors as values in a dict or list; don't nest `try/except` blocks
- `except Exception` is acceptable with a specific fallback action; it is not acceptable as defensive padding
- Don't flatten the error type surface through defensive wrapping; callers can catch unions of types

## Function names

- Prefer short names when the local context makes them unambiguous; prefer longer names when the function is called from far away or by many callers
- Name functions after what they accomplish, not how they do it; implementation-flavored names age poorly when the implementation changes
- Reserve `check_*` for functions that raise on failure; boolean predicates use `is_*` / `has_*` / `*_exists`

## Function dependencies

- Functions take their dependencies as parameters, not by reaching into global state or the stdlib for ambient values
- Entry point means `main()`, `if __name__ == "__main__":` blocks, and CLI translation layers; everywhere else is library code
- Library code does not call `sys.exit`, `sys.stderr.write`, `print`, or `input`; it raises or returns and lets the entry point decide
- Library code does not read environment variables, config files, or command-line arguments; those are resolved by the entry point and passed in
- Library code does not call `datetime.now()`, `time.time()`, `random.random()`, or similar ambient sources when behavior should be testable; inject a clock, RNG, or equivalent
- Global state is a dependency; if a function reads a module-level variable it doesn't own, that variable should be a parameter
- A function you can't call from a test without patching something is one whose ambient dependencies should be parameters

## Function scope

- Identify what a function actually does independent of the current caller's domain; name and scope it at that level
- A function that doesn't touch domain-specific concepts shouldn't have a domain-specific name or signature
- If two functions differ only in hardcoded strings or types, they are one function with a parameter
- Helpers whose bodies only call primitives with pre-filled arguments should be inlined or parameterized, not kept as thin wrappers
- When a function's name implies domain logic but its body is mostly generic primitives, either rename it or add the logic the name promises
- Put generic helpers in generic modules; don't let domain modules accumulate thinly-wrapped utilities
- A useful test: "would this function make sense in a different project?" If yes, it's generic and should be named and placed accordingly

## Tests

- Test files in `tests/` mirror the directory structure of `src/`
- Test classes appear in the same order as the functions they test appear in the source file
- Within a test class, test parameter-validation failures (ValueError etc.) after good-path tests but before bad-path tests that exercise function logic
