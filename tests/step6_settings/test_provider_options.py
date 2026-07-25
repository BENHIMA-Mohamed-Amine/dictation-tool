from providers import PROVIDERS


def test_every_provider_declares_settings_options():
    # The settings window builds a tab per registered provider purely from
    # these attributes, so a provider missing them would render an empty tab.
    for name, cls in PROVIDERS.items():
        assert isinstance(cls.MODELS, list), name
        assert cls.LANGUAGES, f"{name} must offer at least one language"


def test_language_entries_are_label_code_pairs():
    for name, cls in PROVIDERS.items():
        for entry in cls.LANGUAGES:
            label, code = entry
            assert isinstance(label, str) and label, name
            assert code is None or isinstance(code, str), name


def test_auto_detect_is_expressed_as_none():
    from providers.groq import GroqProvider

    labels = dict(GroqProvider.LANGUAGES)
    assert labels["Auto-detect"] is None
