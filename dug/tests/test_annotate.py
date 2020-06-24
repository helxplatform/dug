import pytest

from annotate import Debreviator


class TestAnnotate:
    def test_decode(self):
        test_dict = {
            "diet": "did I eat that?",
            "ftw": "for the win",
            "lmk": "let me know"
        }

        debreviator = Debreviator()
        debreviator.decoder = test_dict

        assert "let me know" == debreviator.decode("lmk")
        assert "for the win" == debreviator.decode("ftw")
        assert "did I eat that?" == debreviator.decode("diet")
