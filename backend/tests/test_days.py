from app.utils.days import CANONICAL_DAYS, is_school_day, normalize_day


class TestNormalizeDay:
    def test_long_form_uppercase(self) -> None:
        assert normalize_day("TUESDAY") == "TUE"

    def test_long_form_titlecase(self) -> None:
        assert normalize_day("Tuesday") == "TUE"

    def test_short_form_lowercase(self) -> None:
        assert normalize_day("tue") == "TUE"

    def test_short_form_already_canonical(self) -> None:
        assert normalize_day("TUE") == "TUE"

    def test_whitespace_is_stripped(self) -> None:
        assert normalize_day("  Wednesday  ") == "WED"

    def test_empty_returns_empty(self) -> None:
        assert normalize_day("") == ""

    def test_none_returns_empty(self) -> None:
        assert normalize_day(None) == ""

    def test_unknown_passes_through_uppercased(self) -> None:
        # Silent pass-through by design: bad values become filter misses,
        # they do not raise and break the request.
        assert normalize_day("xyz") == "XYZ"

    def test_all_school_days_round_trip(self) -> None:
        for canonical in CANONICAL_DAYS:
            assert normalize_day(canonical) == canonical


class TestIsSchoolDay:
    def test_school_days(self) -> None:
        for d in ("Sunday", "monday", "TUE", "wednesday", "Thu"):
            assert is_school_day(d)

    def test_weekend(self) -> None:
        assert not is_school_day("Friday")
        assert not is_school_day("SAT")

    def test_unknown(self) -> None:
        assert not is_school_day("xyz")
        assert not is_school_day("")
        assert not is_school_day(None)
