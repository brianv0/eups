import os, sys, unittest
import os.path
import subprocess
import glob

# This will activate Python 2.6 compatibility hacks
if sys.version_info[:2] == (2, 6):
	import python26compat

testEupsStack = os.path.dirname(__file__)

def setupEnvironment():
    # Add eups modules to PYTHONPATH
    try:
        import eups.utils
    except ImportError:
        eupsPythonPath = os.path.join(os.environ.get("EUPS_DIR", os.path.dirname(testEupsStack)), "python")
        sys.path.append(eupsPythonPath)

        import eups.utils

    # Make sure EUPS_SHELL is defined
    if not "EUPS_SHELL" in os.environ:
        os.environ["EUPS_SHELL"] = "sh"

    # remove any SETUP_ variables
    clenseEnvironment()

def clenseEnvironment():
    # clear out any products setup in the environment as these can interfere 
    # with the tests
    setupvars = [k for k in os.environ.keys() if k.startswith('SETUP_')]
    for var in setupvars:
        del os.environ[var]

# Thought it's typically bad practice to run executable code at the module level,
# we do it here so that any individual test that imports it could be run directly
# from the command line (i.e., `python testFoo.py`)
#
setupEnvironment()

#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
#
# Support code for running unit tests implemented as bash scripts
#
#

def ScriptTestSuite(testSuiteDir):
    """
        A class factory for running a directory full of scripts as
        a Python.unittest test suite. For example, assuming we have a
        directory `foo/`, with scripts `testA.sh` and `testB.sh`, the
        following:

            FooTest = testCommon.ScriptTestSuite("foo")

        will construct a class with members `testA()` and `testB()`, where
        each one will run their corresponding script and fail if it returns
        a non-zero exit code. A full-fledged example can be found in
        testEupspkg.py

        Notes:
          - The given subdirectory is scanned for all files matching
            test*, and a test method is created for each one. Files
            ending in '~' are skipped (these are usually editor backups)
          - if `setup.sh` or `teardown.sh` exist, they will be run from the
            corresponding setUp() and tearDown() unittest methods
          - Scripts must return non-zero exit code to signal failure
          - A test will be skipped if $scriptFilename.skip file exists
            in the subdirectory with scripts. This file can either be:
              - generated by setup.sh (e.g., to test for the existence of
                an interpreter needed to run one of the test scripts), or
              - generated by the test script itself (the script still
                needs to return zero exit code).
          - All scripts must be executable, and begin with an apropriate
            shebang. This class doesn't introspect them in any way, so it's
            theoretically possible to (e.g.) write the tests in Ruby
          - By convention, end shell scripts with .sh and .csh, depending on
            the interpreter used.
          - By convention, use the same name for the Python test file, and
            the subdirectory with the scripts (e.g., testEupspkg.py
            should execute scripts in testEupspkg/)
    """
    def _shouldSkip(self, testFn):
        skipMarkerFn = testFn + ".skip";

        if os.path.isfile(skipMarkerFn):
            if sys.version_info[:2] > (2, 6):
                self.skipTest(open(skipMarkerFn).read())
            else:
                # On Python 2.6 we'll just pretend the test succeeded
                print("Skipping test %s" % testFn)
                return True

        return False

    def setUp(self):
        # chdir into the directory with the scripts
        self.initialDir = os.path.abspath(".")
        os.chdir(self.testDir)

        # Make sure the scripts know to find EUPS
        if "EUPS_DIR" not in os.environ:
            os.environ["EUPS_DIR"] = os.path.dirname(testEupsStack)

        # Make sure there are no products that were setup
        clenseEnvironment()

        # run setup.sh if it exists
        if os.path.isfile("setup.sh"):
            subprocess.check_call("./setup.sh")

    def tearDown(self):
        # run teardown.sh if it exists
        if os.path.isfile("teardown.sh"):
            subprocess.check_call("./teardown.sh")

        # return back to the directory we started from
        os.chdir(self.initialDir)

    def runScriptedTest(self, testFn):
        # test if the test should be skipped
        if self._shouldSkip(testFn):
            return

        try:
            output = subprocess.check_output(testFn, stderr=subprocess.STDOUT, env=os.environ)
        except subprocess.CalledProcessError as e:
            self.fail(("Test %s failed (retcode=%s)\nscript: %s\n" + "~"*32 + " output " + "~"*33 + "\n%s" + "~"*73) % (testFn, e.returncode, testFn, e.output))

        # test if the test was skipped
        self._shouldSkip(testFn)

    testDir = os.path.join(os.path.abspath(os.path.dirname(__file__)), testSuiteDir)

    class_members = {
        "_shouldSkip": _shouldSkip,
        "testDir": testDir,
        "setUp": setUp,
        "tearDown": tearDown,
        "runScriptedTest": runScriptedTest,
    }

    # Discover all tests -- executable files beginning with test
    for testFn in glob.glob(os.path.join(testDir, "test*")):
        if not os.access(testFn, os.X_OK) or testFn.endswith("~"):
            continue
        methodName = os.path.basename(testFn).replace('.', '_')
        class_members[methodName] = lambda self, testFn=testFn: runScriptedTest(self, testFn)

    return type(testSuiteDir, (unittest.TestCase,), class_members)


#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
#
# Support code for running unit tests
#

def makeSuite(testCases, makeSuite=True):
    """Returns a list of all the test suites in testCases (a list of object types); if makeSuite is True,
    return a unittest suite"""

    tests = []
    for t in testCases:
        tests += unittest.makeSuite(t)

    if makeSuite:
        return unittest.TestSuite(tests)
    else:
        return tests

def run(suite, exit=True):
    """Exit with the status code resulting from running the provided test suite"""

    if unittest.TextTestRunner().run(suite).wasSuccessful():
        status = 0
    else:
        status = 1

    if exit:
        sys.exit(status)
    else:
        return status
