import configparser

from mypy.config_parser import parse_config_file
from mypy.options import Options


def test_parse_files_normalization():
    options = Options()
    config = """
    [mypy]
    files = file1.py, file2.py, file3.py, ,
    """

    parser = configparser.ConfigParser()
    parser.read_string(config)

    parse_config_file(options, lambda: None, None, stdout=None, stderr=None)

    # Assert that the trailing commas and empty strings are removed
    assert options.files == ["file1.py", "file2.py", "file3.py"]


def test_parse_files_with_empty_strings():
    options = Options()
    config = """
    [mypy]
    files = ,file1.py,,file2.py
    """
    parser = configparser.RawConfigParser()
    parser.read_string(config)

    parse_config_file(options, lambda: None, None, stdout=None, stderr=None)

    # Assert that empty strings are ignored
    assert options.files == ["file1.py", "file2.py"]
