"""Module for running unittests on the pyboard"""

# getting an error about IsolatedAsyncIoTestCase
# pylint: disable=unused-import

import os
import sys

if os.uname().sysname == 'Linux':
    from typing import Any, Callable, Union, NoReturn
    # Self isn't in typing until 3.11
    from typing_extensions import Self

# pylint: disable=too-many-arguments
# pylint: disable=too-few-public-methods


class SkipTest(Exception):
    """Exception raised if a test should be skipped."""


class AssertRaisesContext:
    """Exception raised if assertRaises is passed a function of None"""

    def __init__(self, exc) -> None:
        self.expected = exc

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_value, tb) -> bool:
        if exc_type is None:
            assert False, f'{self.expected} not raised'
        if issubclass(exc_type, self.expected):
            return True
        return False


# pylint: disable=invalid-name


class TestCase:
    """A single test case"""

    def fail(self, msg: str = '') -> NoReturn:
        """Indicate that something failed"""
        assert False, msg

    def assertEqual(self, x: Any, y: Any, msg: str = '') -> None:
        """Asserts that x and y are equal"""
        if not msg:
            msg = f"{x} vs (expected) {y}"
        assert x == y, msg

    def assertNotEqual(self, x: Any, y: Any, msg: str = '') -> None:
        """Asserts that x and y are not equal."""
        if not msg:
            msg = f"{x} not expected to be equal {y}"
        assert x != y, msg

    def assertAlmostEqual(self,
                          x: Any,
                          y: Any,
                          places: Union[int, None] = None,
                          msg: str = '',
                          delta: Union[float, None] = None) -> None:
        """Asserts that x and y are almost equal."""
        if x == y:
            return
        if delta is not None and places is not None:
            raise TypeError("specify delta or places not both")

        if delta is not None:
            if abs(x - y) <= delta:
                return
            if not msg:
                msg = f'{x} != {y} within {delta} delta'
        else:
            if places is None:
                places = 7
            if round(abs(y - x), places) == 0:
                return
            if not msg:
                msg = f'{x} != {y} within {places} places'

        assert False, msg

    def assertNotAlmostEqual(self,
                             x: Any,
                             y: Any,
                             places=None,
                             msg: str = '',
                             delta=None) -> None:
        """Asserts that x and y are not almost equal"""
        if delta is not None and places is not None:
            raise TypeError("specify delta or places not both")

        if delta is not None:
            if not (x == y) and abs(x - y) > delta:
                return
            if not msg:
                msg = f'{x} == {y} within {delta} delta'
        else:
            if places is None:
                places = 7
            if not (x == y) and round(abs(y - x), places) != 0:
                return
            if not msg:
                msg = f'{x} == {y} within {places} places'

        assert False, msg

    def assertIs(self, x: Any, y: Any, msg: str = '') -> None:
        """Asserts that x is y"""
        if not msg:
            msg = f"{x} is not {y}"
        assert x is y, msg

    def assertIsNot(self, x: Any, y: Any, msg: str = '') -> None:
        """Asserts that x is not y"""
        if not msg:
            msg = f"{x} is {y}"
        assert x is not y, msg

    def assertIsNone(self, x: Any, msg: str = '') -> None:
        """Asserts that x is None"""
        if not msg:
            msg = f"{x} is not None"
        assert x is None, msg

    def assertIsNotNone(self, x: Any, msg: str = '') -> None:
        """Assrtes that x is not None"""
        if not msg:
            msg = f"{x} is None"
        assert x is not None, msg

    def assertTrue(self, x: Any, msg: str = '') -> None:
        """Asserts that x is True"""
        if not msg:
            msg = f"Expected {x} to be True"
        assert x, msg

    def assertFalse(self, x: Any, msg: str = '') -> None:
        """Asserts that x is False"""
        if not msg:
            msg = f"Expected {x} to be False"
        assert not x, msg

    def assertIn(self, x: Any, y: Any, msg: str = '') -> None:
        """Asserts that x is in y"""
        if not msg:
            msg = f"Expected {x} to be in {y}"
        assert x in y, msg

    def assertIsInstance(self, x: Any, y: Any, msg: str = '') -> None:
        """Asserts that x is an instance of y"""
        assert isinstance(x, y), msg

    # pylint: disable=keyword-arg-before-vararg
    def assertRaises(self,
                     exc: Any,
                     func: Union[Callable[[], None], None] = None,
                     *args,
                     **kwargs) -> Union[AssertRaisesContext, None]:
        """Asserts that calling func raises exception exc"""
        if func is None:
            return AssertRaisesContext(exc)

        try:
            func(*args, **kwargs)
            assert False, f"{exc} not raised"
        except Exception as e:
            if isinstance(e, exc):
                return None
            raise


def skip(msg) -> Callable[..., Callable[..., NoReturn]]:
    """Skip decorator"""

    def _decor(_fun) -> Callable[..., NoReturn]:
        """We just replace original fun with _inner"""

        def _inner(_self) -> NoReturn:
            raise SkipTest(msg)

        return _inner

    return _decor


def skipIf(
    cond: bool, msg: str
) -> Union[Callable[..., Any], Callable[..., Callable[..., NoReturn]]]:
    """Skips a test if a condition is true"""
    if not cond:
        return lambda x: x
    return skip(msg)


def skipUnless(
    cond: bool, msg: str
) -> Union[Callable[..., Any], Callable[..., Callable[..., NoReturn]]]:
    """Skips a test unless a condition is true"""
    if cond:
        return lambda x: x
    return skip(msg)


class TestSuite:
    """Class for implementing TestSuites"""

    def __init__(self) -> None:
        self.tests = []

    def addTest(self, cls) -> None:
        """Adds a test to a test suite"""
        self.tests.append(cls)


class TestResult:
    """Result returned from testRunner"""

    def __init__(self) -> None:
        self.errorsNum = 0
        self.failuresNum = 0
        self.skippedNum = 0
        self.testsRun = 0

    def wasSuccessful(self) -> bool:
        """Returns true if the Test Suite was successful"""
        return self.errorsNum == 0 and self.failuresNum == 0


class TestRunner:
    """Runs all of the tests in a test suite"""

    def run(self, suite) -> TestResult:
        """Runs the tests in a suite."""
        res = TestResult()
        for c in suite.tests:
            run_class(c, res)

        print(f"Ran {res.testsRun} tests\n")
        if res.failuresNum > 0 or res.errorsNum > 0:
            print(
                f"FAILED (failures={res.failuresNum}, errors={res.errorsNum})")
        else:
            msg = "OK"
            if res.skippedNum > 0:
                msg += f" ({res.skippedNum} skipped)"
            print(msg)

        return res


def run_class(c, test_result) -> None:
    """Runs all of the tests in a class"""

    o = c()
    set_up = getattr(o, "setUp", lambda: None)
    tear_down = getattr(o, "tearDown", lambda: None)
    for name in dir(o):
        if name.startswith("test"):
            print(f"{name} ({c.__qualname__}) ...", end="")
            m = getattr(o, name)
            set_up()
            try:
                test_result.testsRun += 1
                m()
                print(" ok")
            except SkipTest as e:
                print(" skipped:", e.args[0])
                test_result.skippedNum += 1
            except:  # pylint: disable=bare-except
                print(" FAIL")
                test_result.failuresNum += 1
                # Uncomment to investigate failure in detail
                #raise
                continue
            finally:
                tear_down()


def main(module="__main__") -> NoReturn:
    """Main function to run the unittests"""

    def test_cases(m):
        for tn in dir(m):
            c = getattr(m, tn)
            if isinstance(c, object) and isinstance(c, type) and issubclass(
                    c, TestCase):
                yield c

    m = __import__(module)
    suite = TestSuite()
    for c in test_cases(m):
        suite.addTest(c)
    runner = TestRunner()
    result = runner.run(suite)
    # Terminate with non zero return code in case of failures
    sys.exit(result.failuresNum > 0)
