#!/usr/bin/env python3
"""Apply the plan-time inputs of a recipe: journey bindings, helper aliases, marker aliases.

What an organization owns (the repository a journey runs against, its profile id, its
application validator, the former names of helpers and markers it still declares) is
organization data. The planner reads it from the organization's canon (or, when the canon
cannot be read, from its own last verified read of it) and hands it to the build as
inputs; this tool applies them. It knows the shape of each input, never its content, and
it carries no organization value. Every finding is a warning and the exit status is 0,
except one: a parent image whose identity is a different artifact than the approved one
(`parent`). The last line of standard output is a JSON result with `status` and
`warnings` that the caller can read, and each warning is also written to standard error.

  plan-inputs.py journey --template FILE --output FILE
                         [--repository R] [--profile P] [--validator V]
  plan-inputs.py aliases [--map "ALIAS=TARGET ..."] [--root DIR]
  plan-inputs.py markers [--names "NAME ..."] [--output FILE]
  plan-inputs.py registries [--entries "SCOPE=HOST[=VARIABLE] ..."] [--output FILE]
  plan-inputs.py parent  --reference REF [--approved sha256:HEX] [--resolved sha256:HEX]

journey   FILE is the recipe's template of the document: it fixes the schema and every
          constant, and names each organization fact it binds by a `null` value
          (`repository`, `profile`, `validator`, whichever it has). When every one of
          those facts is given and valid the document is written to --output. Otherwise
          nothing is written, the result says so with a warning, and the build goes on
          as the generic image: a half-resolved binding would present unverified data as
          verified, and no value is ever invented or kept from another organization.
aliases   Each `ALIAS=TARGET` makes the absolute path ALIAS, under /usr/local/, a
          symbolic link to the helper TARGET (a command name in /usr/local/bin or an
          absolute path under /usr/local/). An existing file is never replaced.
markers   Writes the valid names (environment variable names) to the image-owned file
          the emulator helper reads, one per line. The pinned runtime launches the helper
          with a fixed list of environment variables, so the list cannot travel in one.
registries Writes the valid package registry bindings (`<scope>=<host>[=<credential variable
          name>]`) to the image-owned file the web install helper reads. A binding names the
          variable that holds a credential, never a value; an entry of another shape is
          skipped with a warning.
parent    Compares the identity of the parent image with the approved one. The reference
          may be spelled as a tag: that only warns. The resolved digest is the one in the
          reference, or the one the builder observed (`--resolved`). Only a resolved digest
          that differs from the approved one stops (exit 1): it is another artifact. With
          no approved digest, or no way to resolve one, it warns that the parent is
          unverified and goes on.

An input missing from the command line is read from RUNNER_JOURNEY_REPOSITORY,
RUNNER_JOURNEY_PROFILE, RUNNER_JOURNEY_VALIDATOR, RUNNER_HELPER_ALIASES,
RUNNER_ANDROID_MARKER_ALIASES, RUNNER_WEB_REGISTRIES, RUNNER_PARENT_REFERENCE, RUNNER_PARENT_DIGEST and
RUNNER_PARENT_RESOLVED_DIGEST, which is how a Docker build passes its build arguments to
a RUN step.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path, PurePosixPath

REPOSITORY = re.compile(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+')
LOCAL = PurePosixPath('/usr/local')
MAX_LENGTH = 256


def scalar(value):
    return isinstance(value, str) and 0 < len(value) <= MAX_LENGTH and '\n' not in value and '\r' not in value


def repository(value):
    return scalar(value) and REPOSITORY.fullmatch(value) is not None


def validator(value):
    """A canonical relative Python path of the application checkout."""
    if not scalar(value) or '\\' in value:
        return False
    path = PurePosixPath(value)
    return (not path.is_absolute() and path.as_posix() == value and path.suffix == '.py'
            and not any(part in {'', '.', '..'} for part in value.split('/')))


# The organization facts a journey document may bind, and the shape each must have.
FACTS = {'repository': repository, 'profile': scalar, 'validator': validator}


class Usage(ValueError):
    pass


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Usage(message)


def render_journey(template, output, given):
    """Renders one journey binding document from its template, or writes nothing."""
    warnings = []
    result = {'command': 'journey', 'output': str(output), 'warnings': warnings}
    try:
        document = json.loads(Path(template).read_text(encoding='utf-8'))
        if not isinstance(document, dict):
            raise ValueError('not a JSON object')
    except (OSError, ValueError) as error:
        warnings.append(f'the journey template {template} cannot be read ({error}); nothing was written')
        return {**result, 'status': 'not_done', 'source': 'none'}
    wanted = [name for name in FACTS if name in document]
    values = {name: given.get(name) or '' for name in wanted}
    missing = [name for name in wanted if not values[name]]
    invalid = [name for name in wanted if values[name] and not FACTS[name](values[name])]
    if not wanted:
        warnings.append(f'the journey template {template} binds no organization fact; nothing was written')
        return {**result, 'status': 'not_done', 'source': 'none'}
    if missing or invalid:
        if len(missing) == len(wanted):
            warnings.append('no journey binding was resolved from the organization canon; no binding was written '
                            'and the image is built without one (the journey runner will not find a binding to compare)')
        else:
            warnings.append('the journey binding is incomplete or invalid '
                            f'(missing: {", ".join(missing) or "none"}; invalid: {", ".join(invalid) or "none"}); '
                            'no binding was written and the image is built without one')
        return {**result, 'status': 'not_done', 'source': 'none'}
    try:
        write_json(Path(output), {**document, **values})
    except OSError as error:
        warnings.append(f'{output} cannot be written ({error}); the journey binding is unchanged')
        return {**result, 'status': 'not_done', 'source': 'none'}
    return {**result, 'status': 'rendered', 'source': 'plan-inputs'}


def write_json(path, document):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name('.' + path.name + '.part')
    temporary.write_text(json.dumps(document, indent=2) + '\n', encoding='utf-8')
    os.chmod(temporary, 0o644)
    os.replace(temporary, path)


def local_path(value):
    """An absolute path below /usr/local with no `.` or `..` part, or None."""
    if not scalar(value) or '\\' in value:
        return None
    path = PurePosixPath(value)
    if (not path.is_absolute() or path.as_posix() != value or path == LOCAL
            or LOCAL not in path.parents or any(part in {'.', '..'} for part in path.parts)):
        return None
    return path


def link_aliases(spec, root):
    """Links every requested alias to its helper; returns the result."""
    warnings, entries = [], []
    result = {'command': 'aliases', 'aliases': entries, 'warnings': warnings}
    requested = spec.split()
    if not requested:
        return {**result, 'status': 'none', 'note': 'no helper alias was requested; only the neutral helper names are installed'}
    for item in requested:
        alias, _, helper = item.partition('=')
        entry = {'alias': alias, 'target': helper, 'status': 'skipped'}
        entries.append(entry)
        link = local_path(alias)
        target = local_path(helper if '/' in helper else f'/usr/local/bin/{helper}' if helper else '')
        if link is None or target is None:
            warnings.append(f'alias {item!r} is not ALIAS=TARGET with both under /usr/local; skipped')
            continue
        entry['target'] = str(target)
        base = Path(root)
        real_target, real_link = base / str(target).lstrip('/'), base / str(link).lstrip('/')
        try:
            if not (real_target.is_file() and os.access(real_target, os.X_OK)):
                warnings.append(f'helper {target} for alias {link} is not an executable file; skipped')
            elif real_link.is_symlink() and os.readlink(real_link) == str(target):
                entry['status'] = 'ok'
            elif real_link.exists() or real_link.is_symlink():
                warnings.append(f'{link} already exists and is not an alias of {target}; it was not replaced')
            else:
                real_link.parent.mkdir(parents=True, exist_ok=True)
                os.symlink(str(target), real_link)
                entry['status'] = 'ok'
        except OSError as error:
            warnings.append(f'alias {link} -> {target} could not be created ({error}); skipped')
    return {**result, 'status': 'ok' if entries and all(e['status'] == 'ok' for e in entries) else 'partial'}


NAME = re.compile(r'[A-Za-z_][A-Za-z0-9_]{0,127}')
DIGEST = re.compile(r'sha256:[0-9a-f]{64}')
MARKER_FILE = Path('/etc/runner-android-emulator/marker-aliases')


def write_markers(spec, output):
    """Writes the valid marker names to the image-owned file the emulator helper reads."""
    warnings, names = [], []
    result = {'command': 'markers', 'names': names, 'output': str(output), 'warnings': warnings}
    for name in spec.split():
        if not NAME.fullmatch(name):
            warnings.append(f'marker alias {name[:64]!r} is not an environment variable name; skipped')
        elif name not in names:
            names.append(name)
    if not names:
        return {**result, 'status': 'none', 'note': 'no ownership marker alias was requested; only the neutral marker is exported'}
    try:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name('.' + path.name + '.part')
        temporary.write_text('\n'.join(names) + '\n', encoding='utf-8')
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
    except OSError as error:
        warnings.append(f'{output} cannot be written ({error}); the marker aliases were not recorded')
        names.clear()
        return {**result, 'status': 'not_done'}
    return {**result, 'status': 'ok'}


REGISTRY_FILE = Path('/etc/runner-web-stack/registries')
REGISTRY_SCOPE = re.compile(r'@[a-z0-9][a-z0-9._-]*')
REGISTRY_HOST = re.compile(r'[A-Za-z0-9][A-Za-z0-9.-]*(:[0-9]{1,5})?(/[A-Za-z0-9._~/-]*)?')


def registry_entry(entry):
    """True for `<scope>=<host>` or `<scope>=<host>=<credential variable name>`."""
    parts = entry.split('=')
    return (2 <= len(parts) <= 3 and REGISTRY_SCOPE.fullmatch(parts[0]) is not None
            and REGISTRY_HOST.fullmatch(parts[1]) is not None
            and (len(parts) == 2 or NAME.fullmatch(parts[2]) is not None))


def write_registries(spec, output):
    """Writes the valid registry bindings, one per line, to the image-owned file."""
    warnings, entries = [], []
    result = {'command': 'registries', 'entries': entries, 'output': str(output), 'warnings': warnings}
    for entry in spec.split():
        if not registry_entry(entry):
            warnings.append('a registry entry is not <scope>=<host>[=<credential-variable-name>]; skipped')
        elif entry not in entries:
            entries.append(entry)
    if not entries:
        return {**result, 'status': 'none', 'note': 'no registry binding was requested; the install uses the job\'s own npm configuration'}
    try:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name('.' + path.name + '.part')
        temporary.write_text('\n'.join(entries) + '\n', encoding='utf-8')
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
    except OSError as error:
        warnings.append(f'{output} cannot be written ({error}); the registry bindings were not recorded')
        entries.clear()
        return {**result, 'status': 'not_done'}
    return {**result, 'status': 'ok'}


def check_parent(reference, approved, resolved):
    """Compares the parent's resolved digest with the approved one; only a difference is a mismatch."""
    warnings = []
    result = {'command': 'parent', 'reference': reference[:256], 'warnings': warnings}
    qualified = re.search(r'@(sha256:[0-9a-f]{64})$', reference)
    if not reference:
        warnings.append('no parent reference was given; the parent is not verified')
        return {**result, 'status': 'unverified', 'resolved': None}
    if qualified is None:
        warnings.append(f'the parent reference {reference[:128]!r} is not spelled as <image>@sha256:<digest>; '
                        'that is only a spelling, and its resolved digest is what is checked')
    if resolved and not DIGEST.fullmatch(resolved):
        warnings.append(f'the resolved digest {resolved[:80]!r} is not sha256:<64 hex>; it was not used')
        resolved = ''
    if approved and not DIGEST.fullmatch(approved):
        warnings.append(f'the approved digest {approved[:80]!r} is not sha256:<64 hex>; the parent is not verified')
        approved = ''
    if qualified is not None and resolved and resolved != qualified.group(1):
        warnings.append('the resolved digest differs from the digest in the reference; the reference was used')
    actual = qualified.group(1) if qualified is not None else resolved
    result['resolved'] = actual or None
    if not approved:
        warnings.append('no approved digest was given for the parent image; it is not verified against an approved artifact')
        return {**result, 'status': 'unverified'}
    if not actual:
        warnings.append('the digest the parent reference resolves to is not known here (the builder passes it as '
                        'RUNNER_PARENT_RESOLVED_DIGEST); the parent is not verified against the approved digest')
        return {**result, 'status': 'unverified'}
    if actual != approved:
        warnings.append(f'the parent image resolves to {actual}, not to the approved {approved}: it is another artifact')
        return {**result, 'status': 'mismatch'}
    return {**result, 'status': 'verified'}


def parser():
    top = Parser(description=__doc__.splitlines()[0])
    commands = top.add_subparsers(dest='command')
    journey = commands.add_parser('journey')
    journey.add_argument('--template', required=True)
    journey.add_argument('--output', required=True)
    for name in FACTS:
        journey.add_argument(f'--{name}')
    aliases = commands.add_parser('aliases')
    aliases.add_argument('--map')
    aliases.add_argument('--root', default='/')
    markers = commands.add_parser('markers')
    markers.add_argument('--names')
    markers.add_argument('--output', default=str(MARKER_FILE))
    registries = commands.add_parser('registries')
    registries.add_argument('--entries')
    registries.add_argument('--output', default=str(REGISTRY_FILE))
    parent = commands.add_parser('parent')
    parent.add_argument('--reference')
    parent.add_argument('--approved')
    parent.add_argument('--resolved')
    return top


def run(argv, environment):
    try:
        args = parser().parse_args(argv)
        if args.command == 'journey':
            given = {name: getattr(args, name) or environment.get(f'RUNNER_JOURNEY_{name.upper()}', '') for name in FACTS}
            return render_journey(args.template, args.output, given)
        if args.command == 'aliases':
            spec = args.map if args.map is not None else environment.get('RUNNER_HELPER_ALIASES', '')
            return link_aliases(spec, args.root)
        if args.command == 'markers':
            spec = args.names if args.names is not None else environment.get('RUNNER_ANDROID_MARKER_ALIASES', '')
            return write_markers(spec, args.output)
        if args.command == 'registries':
            spec = args.entries if args.entries is not None else environment.get('RUNNER_WEB_REGISTRIES', '')
            return write_registries(spec, args.output)
        if args.command == 'parent':
            pick = lambda value, name: (value if value is not None else environment.get(name, '')).strip()
            return check_parent(pick(args.reference, 'RUNNER_PARENT_REFERENCE'), pick(args.approved, 'RUNNER_PARENT_DIGEST'),
                                pick(args.resolved, 'RUNNER_PARENT_RESOLVED_DIGEST'))
        raise Usage('a command (journey, aliases, markers, registries or parent) is required')
    except Usage as error:
        return {'command': None, 'status': 'not_done', 'warnings': [f'invalid options ({error}); nothing was done']}


def main(argv=None, environment=None):
    result = run(sys.argv[1:] if argv is None else argv, os.environ if environment is None else environment)
    for warning in result['warnings']:
        print('WARNING: ' + warning, file=sys.stderr)
    if result.get('note'):
        print('NOTE: ' + result['note'], file=sys.stderr)
    print(json.dumps(result, sort_keys=True))
    # The one stop: the parent resolves to a different artifact than the approved one.
    return 1 if result.get('status') == 'mismatch' else 0


if __name__ == '__main__':
    raise SystemExit(main())
