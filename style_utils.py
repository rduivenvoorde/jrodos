from PyQt4.QtGui import QColor

class RangeCreator:
    """

    """

    def __init__(self):
        pass

    @staticmethod
    def create_decimal_range(start_exponent=0, end_exponent=100, min_inf=False, max_inf=False):
        """
        Create a Range (a set of tuples) of length l long, making it possible to use the tuples as boundaries
        in a set of rules for a RuleBasedRenderer.

        A Decimal range is something like: ((0,10),(10,100),(100,1000)) or ((1e0,1e1),(1e1,1e2),(1e2,1e3))

        An example      RangeCreator.create_decimal_range(-1, 1)
                        ((0.1, 1), (1, 10))

                        RangeCreator.create_decimal_range(-1, 1, True)
                        ((inf, 0.1), (0.1, 1), (1, 10))

        :param start_exponent:
        :param end_exponent:
        :param min_inf:
        :param max_inf:
        :return: a set with tuples(min, max)
        """
        if (start_exponent % 1) is not 0 or (end_exponent % 1) is not 0:
            raise Exception('"start" and "end" parameter should be a power of 10 in create_decimal_range')

        r = () # empty set
        if min_inf:
            r = (float('inf'), pow(10, start_exponent)),
        for i in range(start_exponent, end_exponent):
            s = pow(10, i)
            e = pow(10, i+1)
            #print '{} - {}'.format(s, e)
            r += (s, e), # add s and e as tuple
        if max_inf:
            r += (pow(10, end_exponent), float('inf')),
            #print r
        return r

    @staticmethod
    def full_cream_color_ramp(count=10, start_hue=0, end_hue=0.66):
        """

        # info about HSV and RGB http://doc.qt.io/qt-4.8/qcolor.html

        :param count:
        :param start_hue:
        :param end_hue:
        :return: and array of count items with colors going from start_hue
        """
        S = 1.0
        V = 1.0
        r = []
        for i in range(0, count):
            H = end_hue * (float(i) / (count - 1))  # *360.0
            color = QColor.fromHsvF(H, S, V, 0.75)
            #r.append(color)
            # nope: other way around
            r.insert(0, color)
        return r

    @staticmethod
    def create_rule_set(start_exponent=0, end_exponent=10, min_inf=False, max_inf=False, start_hue=0, end_hue=0.6):

        bounds = RangeCreator.create_decimal_range(start_exponent, end_exponent, min_inf, max_inf)
        colors = RangeCreator.full_cream_color_ramp(len(bounds))
        r = []
        for i in xrange(len(bounds)):
            # a rule is a set of: label, expression, color
            bound = bounds[i]
            color = colors[i]
            expression = 'Value >= ' + unicode(bound[0]) + ' AND Value < ' + unicode(bound[1])
            label = expression
            rule = (label, expression, color)
            #print rule
            r.append(rule)
        return r

    @staticmethod
    def create_10_colors():
        """
        Create the 10 JRodos colors (The full cream)
        :return:
        """
        # 75% transparency is 'bf'  of 191 in decimaal
        # so 75% transparent red is: #ff0000bf

        # darkblue: #0000ffbf, 0,0,255,0.75
        # bleu2     #3661ffbf 54,97,255,0.75
        # blue3     #38acffbf 56,172,255,0.75
        # blue4     #00ffffbf 0,255,255,0.75
        # green     #91ffb4bf 145,255,180,0.75
        # green2    #d2ff69bf 210,255,105,0.75
        # yellow    #ffff00bf 255,255,0,0.75
        # orange    #ffb700bf 255,183,0,0.75
        # orange2   #ff6f00bf 255,111,0,0.75
        # red       #ff0000bf 255,0,0,0.75

        # http://stackoverflow.com/questions/340209/generate-colors-between-red-and-green-for-a-power-meter
        # R = (255 * n) / 100
        # G = (255 * (100 - n)) / 100
        # B = 0




if __name__ == '__main__':
    RangeCreator.create_decimal_range(-1, 1, True, True)
    #RangeCreator.create_rule_set()
