from base import BaseTestCase


class TestHelpers(BaseTestCase):

    def setUp(self):
        super(TestHelpers, self).setUp()
        import helpers
        self.helpers = helpers

    def test_debug(self):
        assert self.helpers.debug()

    def test_testing(self):
        assert self.helpers.testing()

    def test_natural_list(self):
        result = self.helpers.natural_list([])
        assert result == ""

        result = self.helpers.natural_list(["one"])
        assert result == "one"

        result = self.helpers.natural_list(["one", "two"])
        assert result == "one and two"

        result = self.helpers.natural_list(["one", "two", "three"])
        assert result == "one, two and three"

        result = self.helpers.natural_list(["one", "two", "three", "four"])
        assert result == "one, two, three and four"

    def test_url_quote(self):
        result = self.helpers.url_quote("testing url quoting")
        assert result == "testing+url+quoting"

    def test_attr_escape(self):
        result = self.helpers.attr_escape('"test this"')
        assert result == "&quot;test this&quot;"

    def test_strip_html(self):
        result = self.helpers.strip_html("<script>alert('attack');</script>")
        assert result == "alert('attack');"

    def test_limit(self):
        result = self.helpers.limit("a long string", 13)
        assert result == "a long string"

        result = self.helpers.limit("a long string", 12)
        assert result == "a long st..."

    def test_plural(self):

        # adds s
        result = self.helpers.plural("people")
        assert result == "peoples"

        # doesn't add s if it already exists
        result = self.helpers.plural("peoples")
        assert result == "peoples"

        # handles ending in y
        result = self.helpers.plural("berry")
        assert result == "berries"

    def test_nl2br(self):
        result = self.helpers.nl2br("some text\nwith\nnewlines")
        assert result == "some text<br/>with<br/>newlines"

    
    def test_ordinal(self):
        ordinals = ["First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh", "Eighth", "Ninth", "Tenth"]
        for i in range(len(ordinals)):
            result = self.helpers.ordinal(i + 1)
            assert result == ordinals[i]

        numbers = [11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
        for x in numbers:
            result = self.helpers.ordinal(x)
            assert result == str(x) + "th"

        result = self.helpers.ordinal(21)
        assert result == "21st"

        result = self.helpers.ordinal(22)
        assert result == "22nd"

        result = self.helpers.ordinal(23)
        assert result == "23rd"

    def test_money(self):
        result = self.helpers.money(1)
        assert result == "$0.01"

        result = self.helpers.money(10)
        assert result == "$0.10"

        result = self.helpers.money(100)
        assert result == "$1.00"

        result = self.helpers.money(1000)
        assert result == "$10.00"

        result = self.helpers.money(10000)
        assert result == "$100.00"

        result = self.helpers.money(100000)
        assert result == "$1,000.00"

    def test_int_comma(self):
        result = self.helpers.int_comma(1)
        assert result == "1"

        result = self.helpers.int_comma(10)
        assert result == "10"

        result = self.helpers.int_comma(100)
        assert result == "100"

        result = self.helpers.int_comma(1000)
        assert result == "1,000"

        result = self.helpers.int_comma(10000)
        assert result == "10,000"

        result = self.helpers.int_comma(100000)
        assert result == "100,000"

        result = self.helpers.int_comma(1000000)
        assert result == "1,000,000"
