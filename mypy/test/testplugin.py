from typing import List, Dict
import sys

from mypy.test.helpers import Suite, assert_equal
from mypy.plugins.regex import extract_regex_group_info, RegexPluginException


class RegexPluginSuite(Suite):
    def test_regex_group_analysis(self) -> None:
        def check(pattern: str,
                  expected_mandatory: List[int],
                  expected_total: int,
                  expected_named: Dict[str, int],
                  ) -> None:
            actual_mandatory, actual_total, actual_named = extract_regex_group_info(pattern)
            assert_equal(actual_mandatory, expected_mandatory)
            assert_equal(actual_total, expected_total)
            assert_equal(actual_named, expected_named)

        # Some conventions, to make reading these more clear:
        #
        # m1, m2, m3... -- text meant to be a part of mandatory groups
        # o1, o2, o3... -- text meant to be a part of optional groups
        # x, y, z       -- other dummy filter text
        # n1, n2, n3... -- names for named groups

        # Basic sanity checks
        check(r"x", [0], 1, {})
        check(r"", [0], 1, {})
        check(r"(m1(m2(m3)(m4)))", [0, 1, 2, 3, 4], 5, {})

        # Named groups
        check(r"(?P<n1>m1)(?P=n1)(?P<n2>o2)*", [0, 1], 3, {'n1': 1, 'n2': 2})
        check(r"(?P<n1>foo){0,4} (?P<n2>bar)", [0, 2], 3, {'n1': 1, 'n2': 2})

        # Repetition checks
        check(r"(m1)(o2)?(m3)(o4)*(r5)+(o6)??", [0, 1, 3, 5], 7, {})
        check(r"(m1(o2)?)+", [0, 1], 3, {})
        check(r"(o1){0,3}  (m2){2}  (m3){1,2}", [0, 2, 3], 4, {})
        check(r"(o1){0,3}? (m2){2}? (m3){1,2}?", [0, 2, 3], 4, {})

        # Branching
        check(r"(o1)|(o2)(o3|x)", [0], 4, {})
        check(r"(m1(o2)|(o3))(m4|x)", [0, 1, 4], 5, {})
        check(r"(?:(o1)|(o2))(m3|x)", [0, 3], 4, {})

        # Non-capturing groups
        check(r"(?:x)(m1)", [0, 1], 2, {})
        check(r"(?:x)", [0], 1, {})

        # Flag groups, added in Python 3.6.
        # Note: Doing re.compile("(?a)foo") is equivalent to doing
        # re.compile("foo", flags=re.A). You can also use inline
        # flag groups "(?FLAGS:PATTERN)" to apply flags just for
        # the specified pattern.
        if sys.version_info >= (3, 6):
            check(r"(?s)(?i)x", [0], 1, {})
            check(r"(?si)x", [0], 1, {})
            check(r"(?s:(m1)(o2)*(?P<n3>m3))", [0, 1, 3], 4, {'n3': 3})

        # Lookahead assertions
        check(r"(m1) (?=x)     (m2)", [0, 1, 2], 3, {})
        check(r"(m1) (m2(?=x)) (m3)", [0, 1, 2, 3], 4, {})

        # Negative lookahead assertions
        check(r"(m1) (?!x)     (m2)", [0, 1, 2], 3, {})
        check(r"(m1) (m2(?!x)) (m3)", [0, 1, 2, 3], 4, {})

        # Positive lookbehind assertions
        check(r"(m1)+ (?<=x)(m2)", [0, 1, 2], 3, {})
        check(r"(?<=x)x", [0], 1, {})

        # Conditional matches
        check(r"(?P<n1>m1)  (?(n1)x|y) (m2)", [0, 1, 2], 3, {"n1": 1})
        check(r"(?P<n1>o1)? (?(n1)x|y) (m2)", [0, 2], 3, {"n1": 1})
        check(r"(?P<n1>m1)  (?(n1)x)   (m2)", [0, 1, 2], 3, {"n1": 1})
        check(r"(?P<n1>o1)? (?(n1)x)   (m2)", [0, 2], 3, {"n1": 1})
        check(r"(m1)        (?(1)x|y)  (m2)", [0, 1, 2], 3, {})
        check(r"(o1)?       (?(1)x|y)  (m2)", [0, 2], 3, {})

        # Comments
        check(r"(m1)(?#comment)(r2)", [0, 1, 2], 3, {})

    def test_regex_errors(self) -> None:
        def check(pattern: str) -> None:
            try:
                extract_regex_group_info(pattern)
            except RegexPluginException:
                pass
            else:
                raise AssertionError("Did not throw expection for regex '{}'".format(pattern))

        check(r"(unbalanced")
        check(r"unbalanced)")
        check(r"(?P=badgroupname)")
