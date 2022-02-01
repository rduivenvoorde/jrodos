import unittest
from style_utils import RangeCreator


class TestStyleUtils(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pass

    def setUp(self):
        pass

    def test_create_decimal_range_len(self):
        self.assertIs(1, len(RangeCreator.create_range_set(-1, 1)))
        self.assertIs(2, len(RangeCreator.create_range_set(-1, 1, True)))
        self.assertIs(2, len(RangeCreator.create_range_set(-1, 1, False, True)))
        self.assertIs(3, len(RangeCreator.create_range_set(-1, 1, True, True)))
        self.assertIs(5, len(RangeCreator.create_range_set(-5, 5)))

    def test_create_decimal_range_inf(self):
        self.assertEqual(float('-inf'), RangeCreator.create_range_set(-1, 1, True)[0][0])
        self.assertEqual(float('inf'), RangeCreator.create_range_set(-1, 1, True, True)[-1][1])

    def test_full_cream_color_ramp(self):
        ramp = RangeCreator.full_cream_color_ramp()
        self.assertEqual(10, len(ramp))
        ramp = RangeCreator.full_cream_color_ramp(11)
        self.assertEqual(11, len(ramp))

    def test_create_rule_set(self):
        s = RangeCreator.create_rule_set(-5, 4, False, True)
        print(len(s))
        for r in s:
            print(r)

if __name__ == '__main__':
    unittest.main()
