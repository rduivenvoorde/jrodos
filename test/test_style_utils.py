import unittest
from style_utils import RangeCreator


class TestStyleUtils(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pass

    def setUp(self):
        pass

    def test_create_decimal_range_10power_exception(self):
        with self.assertRaises(Exception):
            RangeCreator.create_decimal_range(3.0)
        with self.assertRaises(Exception):
            RangeCreator.create_decimal_range(0.1, 3)
        with self.assertRaises(Exception):
            RangeCreator.create_decimal_range(0, 3.0, True, True)
        try:
            RangeCreator.create_decimal_range(-3, 10)
        except:
            self.fail('Mmm, should not raise exception')

    def test_create_decimal_range_len(self):
        self.assertIs(2, len(RangeCreator.create_decimal_range(-1, 1)))
        self.assertIs(3, len(RangeCreator.create_decimal_range(-1, 1, True)))
        self.assertIs(3, len(RangeCreator.create_decimal_range(-1, 1, False, True)))
        self.assertIs(4, len(RangeCreator.create_decimal_range(-1, 1, True, True)))
        self.assertIs(10, len(RangeCreator.create_decimal_range(-5, 5)))

    def test_create_decimal_range_inf(self):
        self.assertEquals(float('inf'), RangeCreator.create_decimal_range(-1, 1, True)[0][0])
        self.assertEquals(float('inf'), RangeCreator.create_decimal_range(-1, 1, True, True)[-1][1])

    def test_full_cream_color_ramp(self):
        ramp = RangeCreator.full_cream_color_ramp()
        self.assertEquals(10, len(ramp))
        ramp = RangeCreator.full_cream_color_ramp(11)
        self.assertEquals(11, len(ramp))

    def test_create_rule_set(self):

        # s = RangeCreator.create_rule_set()
        # for r in s:
        #     print r

        s = RangeCreator.create_rule_set(-5, 4, False, True)
        print(len(s))
        for r in s:
            print r

if __name__ == '__main__':
    unittest.main()
