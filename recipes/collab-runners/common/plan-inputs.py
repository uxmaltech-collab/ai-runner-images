#!/usr/bin/env python3
"""Apply the plan-time inputs of a recipe: journey bindings and helper aliases.

What an organization owns (the repository a journey runs against, its profile id, its
application validator, the former names of helpers it still declares) is organization
data. The planner reads it from the organization's canon and hands it to the build as
inputs; this tool applies them. It knows the shape of each input, never its content,
and it carries no organization value. Every finding is a warning and the exit status
is 0: the last line of standard output is a JSON result with `status` and `warnings`
that the caller can read, and each warning is also written to standard error.

  plan-inputs.py journey --fallback FILE --output FILE
                         [--repository R] [--profile P] [--validator V]
  plan-inputs.py aliases [--map "ALIAS=TARGET ..."] [--root DIR]

journey   FILE is the prior verified binding shipped with the recipe: it fixes the
          schema and every constant of the document. When every organization fact the
          document binds (`repository`, `profile`, `validator`, whichever it has) is
          given and valid, they replace the prior values and the document is written
          to --output. Otherwise the prior verified binding is kept as it is and the
          result says so with a warning; a partial or invalid set is never mixed into
          it, because a half-resolved binding would present unverified data as verified.
aliases   Each `ALIAS=TARGET` makes the absolute path ALIAS, under /usr/local/, a
          symbolic link to the helper TARGET (a command name in /usr/local/bin or an
          absolute path under /usr/local/). An existing file is never replaced.

An input missing from the command line is read from RUNNER_JOURNEY_REPOSITORY,
RUNNER_JOURNEY_PROFILE, RUNNER_JOURNEY_VALIDATOR and RUNNER_HELPER_ALIASES, which is
how a Docker build passes its build arguments to a RUN step.
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


def render_journey(fallback, output, given):
    """Returns the result of rendering one journey binding document."""
    warnings = []
    result = {'command': 'journey', 'output': str(output), 'warnings': warnings}
    try:
        prior = json.loads(Path(fallback).read_text(encoding='utf-8'))
        if not isinstance(prior, dict):
            raise ValueError('not a JSON object')
    except (OSError, ValueError) as error:
        warnings.append(f'the prior verified binding {fallback} cannot be read ({error}); nothing was written')
        return {**result, 'status': 'not_done', 'source': 'none'}
    wanted = [name for name in FACTS if name in prior]
    values = {name: given.get(name) or '' for name in wanted}
    missing = [name for name in wanted if not values[name]]
    invalid = [name for name in wanted if values[name] and not FACTS[name](values[name])]
    if wanted and not missing and not invalid:
        document, source = {**prior, **values}, 'plan-inputs'
    else:
        document, source = prior, 'prior-verified'
        if len(missing) == len(wanted):
            warnings.append('no plan-time journey binding was resolved from the organization canon; '
                            'keeping the prior verified binding')
        else:
            warnings.append('the plan-time journey binding is incomplete or invalid '
                            f'(missing: {", ".join(missing) or "none"}; invalid: {", ".join(invalid) or "none"}); '
                            'keeping the prior verified binding and none of the given values')
    try:
        if source == 'plan-inputs' or Path(output).resolve() != Path(fallback).resolve():
            write_json(Path(output), document)
    except OSError as error:
        warnings.append(f'{output} cannot be written ({error}); the journey binding is unchanged')
        return {**result, 'status': 'not_done', 'source': 'none'}
    return {**result, 'status': 'rendered' if source == 'plan-inputs' else 'kept', 'source': source}


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


def parser():
    top = Parser(description=__doc__.splitlines()[0])
    commands = top.add_subparsers(dest='command')
    journey = commands.add_parser('journey')
    journey.add_argument('--fallback', required=True)
    journey.add_argument('--output', required=True)
    for name in FACTS:
        journey.add_argument(f'--{name}')
    aliases = commands.add_parser('aliases')
    aliases.add_argument('--map')
    aliases.add_argument('--root', default='/')
    return top


def run(argv, environment):
    try:
        args = parser().parse_args(argv)
        if args.command == 'journey':
            given = {name: getattr(args, name) or environment.get(f'RUNNER_JOURNEY_{name.upper()}', '') for name in FACTS}
            return render_journey(args.fallback, args.output, given)
        if args.command == 'aliases':
            spec = args.map if args.map is not None else environment.get('RUNNER_HELPER_ALIASES', '')
            return link_aliases(spec, args.root)
        raise Usage('a command (journey or aliases) is required')
    except Usage as error:
        return {'command': None, 'status': 'not_done', 'warnings': [f'invalid options ({error}); nothing was done']}


def main(argv=None, environment=None):
    result = run(sys.argv[1:] if argv is None else argv, os.environ if environment is None else environment)
    for warning in result['warnings']:
        print('WARNING: ' + warning, file=sys.stderr)
    if result.get('note'):
        print('NOTE: ' + result['note'], file=sys.stderr)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
