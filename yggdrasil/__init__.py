r"""This package provides a framework for integrating models across languages
such that they can be run simultaneously, passing input back and forth."""
from yggdrasil import platform
import os
import sys
import glob
import logging
import argparse
import subprocess
import importlib
import contextlib
from ._version import get_versions
_test_package_name = None
_test_package = None
logger = logging.getLogger(__name__)
order = ['pytest', 'nose']
try:
    _test_package_name = order[0]
    _test_package = importlib.import_module(_test_package_name)
except ImportError:  # pragma: debug
    try:
        _test_package_name = order[1]
        _test_package = importlib.import_module(_test_package_name)
    except ImportError:
        _test_package_name = None
        _test_package = None
    

if platform._is_win:  # pragma: windows
    # This is required to fix crash on Windows in case of Ctrl+C
    # https://github.com/ContinuumIO/anaconda-issues/issues/905#issuecomment-232498034
    os.environ['FOR_DISABLE_CONSOLE_CTRL_HANDLER'] = 'T'


@contextlib.contextmanager
def working_directory(path):
    """Changes working directory and returns to previous on exit."""
    prev_cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev_cwd)


def expand_and_add(path, path_list, dir_list):  # pragma: no cover
    r"""Expand the specified path and add it's expanded forms to the provided
    list.

    Args:
        path (str): Absolute/relative path with or without regex wildcard
            expressions to expand.
        path_list (list): Existing list that expansions should be added to.
        dir_list (list): Directories that should be tried for relative paths.

    Returns:
        int: The number of expansions added to path_list.

    """
    if os.path.isabs(path):
        matches = sorted(glob.glob(path))
        path_list += matches
        return len(matches)
    # Try checking for function
    for func_sep in ['::', ':']:
        if (func_sep in path):
            prepath, mod = path.rsplit(func_sep, 1)
            nadded = expand_and_add(prepath, path_list, dir_list)
            if nadded:
                for i in range(-nadded, 0):
                    path_list[i] += '%s%s' % (func_sep, mod)
                return nadded
    # Try directory prefixes
    for path_prefix in dir_list:
        nadded = expand_and_add(os.path.join(path_prefix, path),
                                path_list, dir_list)
        if nadded:
            return nadded
    return 0


def run_tsts(**kwargs):  # pragma: no cover
    r"""Run tests for the package. Relative paths are interpreted to be
    relative to the package root directory.

    Args:
        verbose (bool, optional): If True, set option '-v' which
            increases the verbosity. Defaults to True.
        nocapture (bool, optional): If True, set option '--nocapture'
            ('--capture=no' with pytest) which allows messages to be printed to
            stdout. Defaults to True.
        stop (bool, optional): If True, set option '--stop' ('--exitfirst' for
            pytest) which stops tests at the first failure. Defaults to True.
        nologcapture (bool, optional): If True, set option '--nologcapture'
            which allows logged messages to be printed. Defaults to True.
        withcoverage (bool, optional): If True, set option '--with-coverage'
            which invokes coverage. Defaults to True.
        withexamples (bool, optional): If True, example testing will be
            enabled. Defaults to False.
        language (str, optional): Language to test. Defaults to None
            and all languages will be tested.

    """
    if '-h' not in sys.argv:
        if _test_package is None:
            raise RuntimeError("Could not locate test runner pytest or nose.")
        elif _test_package_name == 'pytest':
            test_cmd = 'pytest'
        elif _test_package_name == 'nose':
            test_cmd = 'nosetests'
        else:
            raise RuntimeError("Unsupported test package: '%s'"
                               % _test_package_name)
    parser = argparse.ArgumentParser(
        description='Run yggdrasil tests.')
    arguments = [
        (['withcoverage', 'with-coverage'], ['nocover', 'no-cover'],
         True, {'help': 'Record coverage during tests.'}),
        (['withexamples', 'with-examples'], ['noexamples', 'no-examples'],
         False, {'help': 'Run example tests when encountered.'}),
        (['longrunning', 'long-running'], ['nolongrunning', 'no-long-running'],
         False, {'help': 'Run long tests when encounterd.'}),
        (['verbose', 'v'], ['quiet'],
         True, {'help': ('Increase verbosity of output from '
                         'the test runner.')}),
        (['nocapture', 's'], ['capture'],
         True, {'help': 'Don\'t capture output from tests.'}),
        (['stop', 'x'], ['dontstop', 'dont-stop'],
         True, {'help': 'Stop after first test failure.'}),
        (['nologcapture'], ['logcapture'],
         True, {'help': ('Don\'t capture output from log '
                         'messages generated during tests.')}),
        (['validatecomponents', 'validate-components'],
         ['skipcomponentvalidation', 'skip-component-validation'],
         False,
         {'help': ('Validate components on creation. This causes '
                   'a decrease in performance so it is turned off '
                   'by default.')})]
    for pos_dest, neg_dest, default, kws in arguments:
        dest = pos_dest[0]
        for x in [pos_dest, neg_dest]:
            for i, y in enumerate(x):
                if len(y) == 1:
                    x[i] = '-' + y
                else:
                    x[i] = '--' + y
        if kwargs.get(dest, default):
            if kws['help'].startswith('Don\'t'):
                kws['help'].split('Don\'t', 1)[-1]
                kws['help'] = kws['help'].replace(
                    kws['help'][0], kws['help'][0].upper(), 1)
            else:
                kws['help'] = kws['help'].replace(
                    kws['help'][0], kws['help'][0].lower(), 1)
                kws['help'] = 'Don\'t ' + kws['help']
            parser.add_argument(*neg_dest, action='store_false',
                                dest=dest, **kws)
        else:
            parser.add_argument(*pos_dest, action='store_true',
                                dest=dest, **kws)
    parser.add_argument('--language', '--languages', default=[],
                        nargs="+", type=str,
                        help='Language(s) that should be tested.')
    parser.add_argument('--ci', action='store_true',
                        help=('Perform addition operations required '
                              'for testing on continuous integration '
                              'services.'))
    suite_args = ('--test-suite', '--test-suites')
    suite_kws = dict(nargs='+', action="extend", type=str,
                     choices=['examples', 'types', 'timing'],
                     help='Test suite(s) that should be run.',
                     dest='test_suites')
    try:
        parser.add_argument(*suite_args, **suite_kws)
    except ValueError:
        # 'extend' introduced in 3.8
        suite_kws['action'] = 'append'
        suite_kws.pop('nargs')
        parser.add_argument(*suite_args, **suite_kws)
    args, extra_argv = parser.parse_known_args()
    initial_dir = os.getcwd()
    package_dir = os.path.dirname(os.path.abspath(__file__))
    error_code = 0
    # Peform ci tests/operations
    # Call bash script?
    if args.ci:
        extra_argv += ['-c', 'setup.cfg', '--cov-config=.coveragerc']
    # Separate out paths from options
    argv = [test_cmd]
    test_paths = []
    opt_val = 0
    for x in extra_argv:
        if opt_val > 0:
            argv.append(x)
            opt_val -= 1
        elif x.endswith('yggtest'):
            pass
        elif x.startswith('-'):
            argv.append(x)
            if (_test_package_name == 'pytest') and (x in ['-c']):
                opt_val = 1
        else:
            test_paths.append(x)
    if args.test_suites:
        for x in args.test_suites:
            if x == 'examples':
                args.withexamples = True
                test_paths.append('examples')
            elif x == 'types':
                args.withexamples = True
                args.longrunning = True
                test_paths.append(os.path.join('examples', 'tests',
                                               'test_types.py'))
            elif x == 'timing':
                args.longrunning = True
                test_paths.append(os.path.join('tests', 'test_timing.py'))
    if _test_package_name == 'nose':
        argv += ['--detailed-errors', '--exe']
    if args.verbose:
        argv.append('-v')
    if args.nocapture:
        argv.append('-s')
    if args.stop:
        argv.append('-x')
    if args.nologcapture and (_test_package_name == 'nose'):
        argv.append('--nologcapture')
    if args.withcoverage:
        if _test_package_name == 'nose':
            argv.append('--with-coverage')
            argv.append('--cover-package=yggdrasil')
        elif _test_package_name == 'pytest':
            argv.append('--cov=%s' % package_dir)
    # Get expanded tests to allow for paths that are relative to either the
    # yggdrasil root directory or the current working directory
    expanded_test_paths = []
    if not test_paths:
        expanded_test_paths.append(package_dir)
    else:
        for x in test_paths:
            if not expand_and_add(x, expanded_test_paths,
                                  [package_dir, os.getcwd()]):
                expanded_test_paths.append(x)
    argv += expanded_test_paths
    # Run test command and perform cleanup before logging any errors
    logger.info("Running %s from %s", argv, os.getcwd())
    old_env = {}
    pth_file = 'ygg_coverage.pth'
    assert(not os.path.isfile(pth_file))
    try:
        # Set env
        if args.withexamples:
            old_env['YGG_ENABLE_EXAMPLE_TESTS'] = os.environ.get(
                'YGG_ENABLE_EXAMPLE_TESTS', None)
            os.environ['YGG_ENABLE_EXAMPLE_TESTS'] = 'True'
        if args.language:
            from yggdrasil.components import import_component
            args.language = [import_component('model', x).language
                             for x in args.language]
            old_env['YGG_TEST_LANGUAGE'] = os.environ.get(
                'YGG_TEST_LANGUAGE', None)
            os.environ['YGG_TEST_LANGUAGE'] = ','.join(args.language)
        if args.longrunning:
            old_env['YGG_ENABLE_LONG_TESTS'] = os.environ.get(
                'YGG_ENABLE_LONG_TESTS', None)
            os.environ['YGG_ENABLE_LONG_TESTS'] = 'True'
        if args.withcoverage:
            old_env['COVERAGE_PROCESS_START'] = os.environ.get(
                'COVERAGE_PROCESS_START', None)
            os.environ['COVERAGE_PROCESS_START'] = 'True'
            with open(pth_file, 'w') as fd:
                fd.write("import coverage; coverage.process_startup()")
        if args.test_suites and ('timing' in args.test_suites):
            old_env['YGG_TEST_PRODUCTION_RUNS'] = os.environ.get(
                'YGG_TEST_PRODUCTION_RUNS', None)
            os.environ['YGG_TEST_PRODUCTION_RUNS'] = 'True'
        if not args.validatecomponents:
            old_env['YGG_SKIP_COMPONENT_VALIDATION'] = os.environ.get(
                'YGG_SKIP_COMPONENT_VALIDATION', None)
            if old_env['YGG_SKIP_COMPONENT_VALIDATION'] is None:
                os.environ['YGG_SKIP_COMPONENT_VALIDATION'] = 'True'
        # Perform CI specific pretest operations
        if args.ci:
            top_dir = os.path.dirname(os.getcwd())
            src_cmd = ('python -c \'import versioneer; '
                       'print(versioneer.get_version())\'')
            dst_cmd = ('python -c \'import yggdrasil; '
                       'print(yggdrasil.__version__)\'')
            src_ver = subprocess.check_output(src_cmd, shell=True)
            dst_ver = subprocess.check_output(dst_cmd, shell=True,
                                              cwd=top_dir)
            if src_ver != dst_ver:  # pragma: debug
                raise RuntimeError(("Versions do not match:\n"
                                    "\tSource version: %s\n"
                                    "\tBuild  version: %s\n")
                                   % (src_ver, dst_ver))
            if os.environ.get("INSTALLR", None) == "1":
                from yggdrasil import tools
                print(tools.which("R"))
                print(tools.which("Rscript"))
            subprocess.check_call(["flake8", "yggdrasil"])
            if os.environ.get("YGG_CONDA", None):
                subprocess.check_call(["python", "create_coveragerc.py"])
            if not os.path.isfile(".coveragerc"):
                raise RuntimeError(".coveragerc file dosn't exist.")
            with open(".coveragerc", "r") as fd:
                print(fd.read())
            subprocess.check_call(["ygginfo", "--verbose"])
        error_code = subprocess.call(argv)
    except BaseException:
        logger.exception('Error in running test.')
        error_code = -1
    finally:
        os.chdir(initial_dir)
        for k, v in old_env.items():
            if v is None:
                del os.environ[k]
            else:
                os.environ[k] = v
        if os.path.isfile(pth_file):
            os.remove(pth_file)
    return error_code


__all__ = []
__version__ = get_versions()['version']
del get_versions
