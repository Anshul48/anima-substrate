import unittest

from statslite import moving_average


class BasicTest(unittest.TestCase):
    def test_window_two(self):
        self.assertEqual(moving_average([1, 2, 3, 4], 2), [1.5, 2.5, 3.5])


if __name__ == "__main__":
    unittest.main()
