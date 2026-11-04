"""Hidden checker tests. The agent never sees this file; it is copied into a
separate evaluation copy only after the agent has finished."""
import unittest

from statslite import moving_average


class HiddenTest(unittest.TestCase):
    def test_window_two(self):
        self.assertEqual(moving_average([1, 2, 3, 4], 2), [1.5, 2.5, 3.5])

    def test_window_equals_length_gives_one_value(self):
        self.assertEqual(moving_average([2, 4, 6], 3), [4.0])

    def test_window_one_is_identity(self):
        self.assertEqual(moving_average([5, 7, 9], 1), [5.0, 7.0, 9.0])

    def test_window_larger_than_data_gives_empty_list(self):
        self.assertEqual(moving_average([1, 2], 5), [])

    def test_empty_values_gives_empty_list(self):
        self.assertEqual(moving_average([], 2), [])

    def test_window_must_be_positive(self):
        for bad in (0, -1):
            with self.assertRaises(ValueError):
                moving_average([1, 2, 3], bad)

    def test_input_is_not_modified(self):
        data = [3, 6, 9]
        moving_average(data, 2)
        self.assertEqual(data, [3, 6, 9])


if __name__ == "__main__":
    unittest.main()
