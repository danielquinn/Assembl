from unittest import TestCase, mock, skip

from ..views import AutocompleteView


class AutocompleteViewTestCase(TestCase):

    @mock.patch("src.views.AutocompleteView._get_species")
    @mock.patch("src.views.AutocompleteView._get_query")
    @mock.patch("src.views.AutocompleteView._get_limit")
    @mock.patch("src.views.AutocompleteView._get_from_cache")
    @mock.patch("src.views.AutocompleteView._get_from_db")
    @mock.patch("src.views.AutocompleteView._render")
    def test_get(self, render, get_from_db, get_from_cache,
                 get_limit, get_query, get_species):
        """
        Test the various permutations of how get() will respond to input and
        the environment.
        :param render: A mock of ``AutocompleteView._render()``
        :param get_from_db: A mock of ``AutocompleteView.get_form_db()``
        :param get_from_cache: A mock of ``AutocompleteView.get_from_cache()``
        :param get_limit: A mock of ``AutocompleteView._get_limit()``
        :param get_query: A mock of ``AutocompleteView._get_query()``
        :param get_species: A mock of ``AutocompleteView._get_species()``
        """

        cases = (
            ("",        "query", "limit", ["cache"], ["db"], False, 0, 0, []),
            ("species", "",      "limit", ["cache"], ["db"], False, 0, 0, []),
            ("species", "q",     "limit", ["cache"], ["db"], False, 0, 0, []),
            ("species", "qu",    "limit", ["cache"], ["db"], False, 0, 0, []),
            ("species", "query", "limit", ["cache"], ["db"], False, 0, 1, ["db"]),  # NOQA: E501
            ("species", "query", "limit", ["cache"], ["db"], True,  1, 0, ["cache"]),  # NOQA: E501
        )

        for case in cases:

            # Reset counters
            get_from_cache.call_count = 0
            get_from_db.call_count = 0

            get_species.return_value = case[0]
            get_query.return_value = case[1]
            get_limit.return_value = case[2]
            get_from_cache.return_value = case[3]
            get_from_db.return_value = case[4]

            AutocompleteView(aggressive_caching_enabled=case[5]).get()

            message = "Arguments were: {}".format(case[:3] + (case[5],))

            self.assertEqual(get_from_cache.call_count, case[6], message)
            self.assertEqual(get_from_db.call_count, case[7], message)
            self.assertEqual(render.call_args[0][0], case[8], message)

    @mock.patch("src.views.AutocompleteView.CACHE")
    def test_populate_cache(self, *args):

        m = mock.mock_open(read_data='{"species": ["x", "y"]}')
        with mock.patch("src.views.open", m, create=True):
            AutocompleteView().populate_cache()

        self.assertEqual(AutocompleteView.CACHE, {"species": ["x", "y"]})

    def test__render(self):
        self.assertEqual(
            AutocompleteView()._render({"x": "y"}),
            ('{"x":"y"}', 200, {"Content-Type": "application/json"})
        )

    @skip("Mocking SQLAlchemy is a PITA and there's no real magic here anyway")
    def test__get_from_db(self):
        pass

    @mock.patch("src.views.AutocompleteView.CACHE", {"alpha": ["abc", "abcde", "xyzabc"]})  # NOQA: E501
    @mock.patch("src.views.AutocompleteView._cleanup_label", lambda _, x: x)
    def test__get_from_cache(self):
        cases = (
            (("alpha", "abc",  5), ["abc", "abcde", "xyzabc"]),
            (("alpha", "abc",  2), ["abc", "abcde"]),
            (("alpha", "xyz",  5), ["xyzabc"]),
            (("alpha", "xy z", 5), []),
            (("bravo", "abc",  5), []),
        )
        for case in cases:
            self.assertEqual(
                AutocompleteView()._get_from_cache(*case[0]),
                case[1],
                "Arguments were: {}".format(case)
            )

    @skip("Unnecessary")
    def test__get_query(self):
        pass

    @mock.patch("src.views.AutocompleteView.DEFAULT_LIMIT", 10)
    @mock.patch("src.views.AutocompleteView.MAXIMUM_LIMIT", 25)
    @mock.patch("src.views.request")
    def test__get_limit(self, m):
        cases = (
            (10, 10),
            ("10", 10),
            (26, 25),
            ("26", 25),
            (1, 1),
            (0, 10),
            (-1, 10),
            ("seven", 10)
        )
        for case in cases:
            arg, expected = case
            m.args = {"limit": arg}
            self.assertEqual(
                AutocompleteView()._get_limit(),
                expected,
                "Arguments were: {}".format(case)
            )

    @skip("Unnecessary")
    def test__get_species(self):
        pass

    @mock.patch("src.views.request")
    def test__sanitise_input(self, m):
        cases = (
            ("asdf", "asdf"),
            ("as df", "as df"),
            ("as%df", "asdf"),
            ("as!df", "asdf"),
            ("as'df", "asdf"),
            ("as(d)f", "as(d)f"),
            ('"asdf"', "asdf"),
        )
        for case in cases:
            arg, expected = case
            m.args = {"x": arg}
            self.assertEqual(
                AutocompleteView._sanitise_input("x"),
                expected,
                "Arguments were: {}".format(case)
            )

    def test__cleanup_label(self):
        cases = (
            ("asdf", "ASDF"),
            ("as df", "AS df"),
            ("as (df)", "AS (df)"),
        )
        for case in cases:
            arg, expected = case
            self.assertEqual(
                AutocompleteView._cleanup_label(arg),
                expected,
                "Arguments were: {}".format(case)
            )
