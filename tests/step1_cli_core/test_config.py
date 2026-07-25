from config import ConfigStore, DEFAULTS


def test_load_defaults_when_no_file(tmp_path):
    store = ConfigStore(config_dir=tmp_path)
    assert store.load() == DEFAULTS


def test_save_then_load_round_trip(tmp_path):
    store = ConfigStore(config_dir=tmp_path)
    data = {"selected_provider": "soniox", "keyterms": ["kubernetes", "anthropic"]}

    store.save(data)
    loaded = ConfigStore(config_dir=tmp_path).load()

    # Not an equality check: load() fills in any key the saved file predates,
    # so a config written before a new setting existed still loads.
    assert loaded == {**DEFAULTS, **data}
