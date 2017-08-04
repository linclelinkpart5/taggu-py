import unittest
import itertools as it

import taggu.invoker as ti


class TestInvoker(unittest.TestCase):
    def test_validate_types_a(self):
        # Simple case.
        args = (1, 'test', 1.5)
        types = (int, str, float)
        more_ok = False
        self.assertTrue(ti.validate_types(args=args, types=types, more_ok=more_ok))

        # Choices for each position.
        args = (1, 'test', 1.5)
        types = ((int, set), (str, int), (float, dict))
        more_ok = False
        self.assertTrue(ti.validate_types(args=args, types=types, more_ok=more_ok))

        # Extra types OK if flag is set.
        args = (1, 'test', 1.5)
        types = (int, str, float, dict)
        more_ok = True
        self.assertTrue(ti.validate_types(args=args, types=types, more_ok=more_ok))

        types = (int, str, float, dict, set, tuple)
        self.assertTrue(ti.validate_types(args=args, types=types, more_ok=more_ok))

    def test_validate_types_b(self):
        # Extra arg.
        args = (1, 'test', 1.5, 'extra arg')
        types = (int, str, float)
        more_ok = False
        self.assertFalse(ti.validate_types(args=args, types=types, more_ok=more_ok))

        # Extra type.
        args = (1, 'test', 1.5)
        types = (int, str, float, dict)
        more_ok = False
        self.assertFalse(ti.validate_types(args=args, types=types, more_ok=more_ok))

        # Type mismatch.
        args = (1, 'test', 1.5)
        types = (str, str, float)
        more_ok = False
        self.assertFalse(ti.validate_types(args=args, types=types, more_ok=more_ok))

    def test_validate_types_c(self):
        # Infinite generator of str type classes.
        always_str = it.repeat(str)

        for n in range(5):
            args = tuple(f'arg_{i}' for i in range(n))
            types = always_str
            more_ok = True
            self.assertTrue(ti.validate_types(args=args, types=types, more_ok=more_ok))

            more_ok = False
            self.assertFalse(ti.validate_types(args=args, types=types, more_ok=more_ok))

    def test_normalize_arg_sequence_a(self):
        args = (1, 2, 3)
        desired_len = 6
        def_vals = (4, 5, 6)
        normalized = ti.normalize_arg_sequence(args=args, desired_len=desired_len, def_vals=def_vals)
        self.assertEqual((1, 2, 3, 4, 5, 6), normalized)

        desired_len = 5
        normalized = ti.normalize_arg_sequence(args=args, desired_len=desired_len, def_vals=def_vals)
        self.assertEqual((1, 2, 3, 5, 6), normalized)

        desired_len = 4
        normalized = ti.normalize_arg_sequence(args=args, desired_len=desired_len, def_vals=def_vals)
        self.assertEqual((1, 2, 3, 6), normalized)

        desired_len = 3
        normalized = ti.normalize_arg_sequence(args=args, desired_len=desired_len, def_vals=def_vals)
        self.assertEqual((1, 2, 3), normalized)

        args = ()
        desired_len = 3
        def_vals = (1, 2, 3)
        normalized = ti.normalize_arg_sequence(args=args, desired_len=desired_len, def_vals=def_vals)
        self.assertEqual((1, 2, 3), normalized)

        args = (1, 2, 3)
        desired_len = 3
        normalized = ti.normalize_arg_sequence(args=args, desired_len=desired_len)
        self.assertEqual((1, 2, 3), normalized)

    def test_normalize_arg_sequence_b(self):
        args = (1, 2, 3, 4)
        desired_len = 5
        def_vals = ()
        with self.assertRaises(ti.NotEnoughArgsException):
            ti.normalize_arg_sequence(args=args, desired_len=desired_len, def_vals=def_vals)

        args = (1, 2, 3, 4, 5, 6)
        desired_len = 5
        def_vals = ()
        with self.assertRaises(ti.TooManyArgsException):
            ti.normalize_arg_sequence(args=args, desired_len=desired_len, def_vals=def_vals)


if __name__ == '__main__':
    unittest.main()
