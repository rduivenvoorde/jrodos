import math

from qgis.PyQt.QtGui import (
    QColor,
)
from qgis.core import (
    QgsRuleBasedRenderer,
    QgsSymbol,
)

import logging
from . import LOGGER_NAME
log = logging.getLogger(LOGGER_NAME)


class RangeCreator:
    """

    """

    SLD_TEMPLATE = """<?xml version="1.0" ?>
<StyledLayerDescriptor>
<NamedLayer>
  <Name>jrodoslayer</Name>
  <UserStyle xmlns="http://www.opengis.net/sld">
    <Name>Default Styler</Name>
    <Title>Custom Created SLD 1</Title>
    <Abstract/>
    <FeatureTypeStyle>
      <Name>Value</Name>
      <Title>Custom Created SLD 2</Title>
      <Abstract>abstract</Abstract>
      <FeatureTypeName>Feature</FeatureTypeName>
      <SemanticTypeIdentifier>generic:geometry</SemanticTypeIdentifier>
      <!-- START rules -->
      {rules}
      <!-- END rules -->         
    </FeatureTypeStyle>
  </UserStyle>
</NamedLayer>
</StyledLayerDescriptor>"""

    examples = """
      <Rule>
        <Name>name</Name>
        <Title>&gt;1E1</Title>
        <Abstract>Abstract</Abstract>
        <Filter xmlns="http://www.opengis.net/ogc">
          <PropertyIsGreaterThanOrEqualTo>
            <PropertyName>Value</PropertyName>
            <Literal>1.0E1</Literal>
          </PropertyIsGreaterThanOrEqualTo>
        </Filter>
        <PolygonSymbolizer>
          <Fill>
            <CssParameter name="fill">#FF0000</CssParameter>
            <CssParameter name="fill-opacity">0.75</CssParameter>
          </Fill>
        </PolygonSymbolizer>
      </Rule>
      
      <Rule>
        <Name>name</Name>
        <Title>{title}</Title>
        <Abstract>{abstract}</Abstract>
        <Filter xmlns="http://www.opengis.net/ogc">
          <PropertyIsBetween>
            <PropertyName>Value</PropertyName>
            <LowerBoundary>
              <Literal>1.0E0</Literal>
            </LowerBoundary>
            <UpperBoundary>
              <Literal>1.0E1</Literal>
            </UpperBoundary>
          </PropertyIsBetween>
        </Filter>
        <PolygonSymbolizer>
          <Fill>
            <CssParameter name="fill">#FF6F00</CssParameter>
            <CssParameter name="fill-opacity">0.75</CssParameter>
          </Fill>
        </PolygonSymbolizer>
      </Rule>"""
    # needs: title, abastract, lowerboundary, upperboundary, fill (hex string like #ff0000), opacity
    SLD_RULE_TEMPLATE = """
          <Rule>
            <Name>name</Name>
            <Title>{title}</Title>
            <Abstract>{abstract}</Abstract>
            <Filter xmlns="http://www.opengis.net/ogc">
              <PropertyIsBetween>
                <PropertyName>Value</PropertyName>
                <LowerBoundary>
                  <Literal>{lower_boundary}</Literal>
                </LowerBoundary>
                <UpperBoundary>
                  <Literal>{upper_boundary}</Literal>
                </UpperBoundary>
              </PropertyIsBetween>
            </Filter>
            <PolygonSymbolizer>
              <Fill>
                <CssParameter name="fill">{fill}</CssParameter>
                <CssParameter name="fill-opacity">0.75</CssParameter>
              </Fill>
            </PolygonSymbolizer>
          </Rule>"""


    def __init__(self):
        pass

    @staticmethod
    def create_log_range_set(start=0, end=100, min_inf=False, max_inf=False):
        """
        Create a Range (a set of tuples) of length l long, making it possible to use the tuples as boundaries
        in a set of rules for a RuleBasedRenderer.

        A Decimal range is something like: ((0,10),(10,100),(100,1000)) or ((1e0,1e1),(1e1,1e2),(1e2,1e3))

        An example      RangeCreator.create_log_range_set(-1, 1)
                        ((0.1, 1), (1, 10))

                        RangeCreator.create_log_range_set(-1, 1, True)
                        ((inf, 0.1), (0.1, 1), (1, 10))

        :param start:
        :param end:
        :param min_inf:
        :param max_inf:
        :return: a set with tuples(min, max)
        """
        if (start % 1) != 0 or (end % 1) != 0:
            raise Exception('"start" and "end" parameter should be a power of 10 in create_decimal_range')

        r = ()  # empty set
        if min_inf:
            r = (-float('inf'), pow(10, start)),
        for i in range(start, end):
            s = pow(10, i)
            e = pow(10, i+1)
            #print '{} - {}'.format(s, e)
            r += (s, e),  # add s and e as tuple
        if max_inf:
            #r += (pow(10, end_exponent), float('inf')),
            r += (pow(10, end), 1000000000000),
            #print r
        return r

    @staticmethod
    def create_range_set(start=0, end=100, min_inf=False, max_inf=False, step=2):
        """
        Create a Range (a set of tuples) of length l long, making it possible to use the tuples as boundaries
        in a set of rules for a RuleBasedRenderer.

        A range is something like: ((0,2),(2,4),(4,6))

        An example      RangeCreator.create_range_set(0.23, 8)
                        ((0, 2), (2, 4), (4, 6), (6, 8))

                        RangeCreator.create_range_set(0.23, 8, True)
                        ((-inf, 0), (0, 2), (2, 4), (4, 6), (6, 8))

        :param start:
        :param end:
        :param min_inf:
        :param max_inf:
        :param step:
        :return: a set with tuples(min, max)
        """

        r = ()  # empty set
        if min_inf:
            r = (-float('inf'), math.floor(start)),
        # if step is an integer:
        #for i in range(math.floor(start), math.ceil(end), step):
        # but we also want to be able to use a float here:
        stepsize = (end-start)/step
        s = start
        e = end
        while s < end:
            e = s+step
            # while loop fails with rounding errors when floats, extra check
            # to stop when we are really (that is more then 1 percent) over the end
            if e > 1.01*end:
                break
            #print '{} - {}'.format(s, e)
            r += (s, e),  # add s and e as tuple
            s = s+step
        if max_inf:
            #r += (pow(10, end_exponent), float('inf')),
            r += (math.ceil(end), float('inf')),
            #print r
        return r

    @staticmethod
    def full_cream_color_ramp(count=10, start_hue=0, end_hue=0.66, hex_notation=False, reverse=False):
        """
        This returns a full cream array of QColors (or hex notation like '#ff0000' == QColor.name())
        Defaulting from Blue to Red (from cold to hot)

        # info about HSV and RGB http://doc.qt.io/qt-4.8/qcolor.html
        # via https://docs.python.org/3/library/colorsys.html also
        # http://poynton.ca/notes/colour_and_gamma/ColorFAQ.html
        # and
        # https://www.cambridgeincolour.com/tutorials/color-spaces.htm

        :param count:
        :param start_hue:
        :param end_hue:
        :param hex_notation:
        :param reverse:
        :return: an array of <count> items with colors going from <start_hue>
        """
        S = 1.0
        V = 1.0
        r = []
        # create an even range from 0 to end_hue(default 0.66) so  with
        # count = 3, you will get: 0.0, 0.33, 0.66
        for i in range(0, count):
            H = end_hue * (float(i) / (count - 1))
            from qgis.PyQt.QtGui import QColor
            qcolor = QColor.fromHsvF(H, S, V, 0.75)
            if hex_notation:
                color = qcolor.name()
            else:
                color = qcolor
            if reverse:
                # red to blue
                r.append(color)
            else:
                # default: other way around:
                # blue to red
                r.insert(0, color)

            #print(qcolor.name())
            ## the same but pythonic way:
            #import colorsys
            #import math
            #t = colorsys.hsv_to_rgb(H, S, V)  # returns a tuple like (0.0, 0.48, 1.0)
            #l = list(t)  # [0.0, 0.48, 1.0]
            #rgbl = [math.floor(il * 255) for il in l]  # multiply all items in the list with 255
            #color = '#%02x%02x%02x' % tuple(rgbl)
            #print(color)
            # r.insert(0, color)
        return r

    @staticmethod
    def create_rule_set(start=0, end=10, class_count=10, min_inf=False, max_inf=False, start_hue=0, end_hue=0.66, hex_notation=False, reverse=False, decimals=3):
        """
        This creates a "ruleset" of class_count items, in which every item has 3 members/items:
        - first one is the LABEL to use (in the QGIS or SLD style)
        - second one is the EXPRESSION to use (in the QGIS or SLD style)
        - third one is the COLOR to use to use (in the QGIS or SLD style)
        :param start:
        :param end:
        :param class_count:
        :param min_inf:
        :param max_inf:
        :param start_hue:
        :param end_hue:
        :return:
        """
        step = (end-start)/class_count
        bounds = RangeCreator.create_range_set(start, end, min_inf, max_inf, step=step)
        colors = RangeCreator.full_cream_color_ramp(len(bounds), start_hue, end_hue, hex_notation=hex_notation, reverse=reverse)
        r = []
        for i in range(len(bounds)):
            # a rule is a set of: label, expression, color
            bound = bounds[i]
            color = colors[i]
            # note: INCLUDING lower limit, EXCLUDING upper limit !
            expression = f'Value >= {bound[0]} AND Value < {bound[1]}'
            if decimals == 3:
                label = f'Value >= {bound[0]:.3f} AND Value < {bound[1]:.3f}'
            elif decimals == 0:
                label = f'{bound[0]} - {bound[1]} uur'
            rule = (label, expression, color)
            #print rule
            r.append(rule)
        return r

    @staticmethod
    def create_cloud_ruleset(max_value):
        hours = {
            # hours  #classes, stepsize(hr)
            2: [8, 0.15],
            4: [8, 0.5],
            6: [6, 1],
            12: [12, 1],
            24: [12, 2],
            48: [12, 4],
            72: [12, 6],
            96: [12, 8],
            120: [10, 12],
            192: [8, 24],
        }
        hour = 0
        for hour, info in hours.items():
            if hour >= max_value:
                # create_rule_set(start=0, end=10, class_count=10, min_inf=False, max_inf=False, start_hue=0, end_hue=0.66, hex_notation=False, reverse=False)
                break
        return RangeCreator.create_rule_set(0, hour, class_count=info[0], min_inf=False, max_inf=False, reverse=True, decimals=0)

    @staticmethod
    def create_log_rule_set(start_exponent=0, end_exponent=10, min_inf=False, max_inf=False, start_hue=0, end_hue=0.66, hex_notation=False, reverse=False):
        bounds = RangeCreator.create_log_range_set(start_exponent, end_exponent, min_inf, max_inf)
        colors = RangeCreator.full_cream_color_ramp(len(bounds), start_hue, end_hue, hex_notation=hex_notation, reverse=reverse)
        r = []
        for i in range(len(bounds)):
            # a rule is a set of: label, expression, color
            bound = bounds[i]
            color = colors[i]
            # note: INCLUDING lower limit, EXCLUDING upper limit !
            expression = 'Value >= ' + str(bound[0]) + ' AND Value < ' + str(bound[1])
            label = expression
            rule = (label, expression, color)
            #print rule
            r.append(rule)
        return r

    @staticmethod
    def create_log_sld(start_exponent=0, end_exponent=None, min_inf=False, max_inf=False, start_hue=0, end_hue=0.66, hex_notation=False, reverse=False):
        # default to 10 classes if end_exponent (or both start and end) are not given as parameters
        if end_exponent is None:
            end_exponent = start_exponent + 10
        bounds = RangeCreator.create_log_range_set(start_exponent, end_exponent, min_inf, max_inf)
        colors = RangeCreator.full_cream_color_ramp(len(bounds), start_hue, end_hue, hex_notation=hex_notation, reverse=reverse)
        rules = []
        for i in range(len(bounds)):
            #print(f'{colors[i]}, {bounds[i]})
            lower = bounds[i][0]
            upper = bounds[i][1]
            rule = RangeCreator.SLD_RULE_TEMPLATE.format(
                lower_boundary=lower,
                upper_boundary=upper,
                title=f'{lower} - {upper}',
                abstract=f'{lower} - {upper}',
                fill=colors[i])
            rules.append(rule)
        return RangeCreator.SLD_TEMPLATE.format(rules=''.join(rules))

    @staticmethod
    def create_sld(start=0, end=24, min_inf=False, max_inf=False, step=2.0, start_hue=0, end_hue=0.66):
        bounds = RangeCreator.create_range_set(start, end, min_inf, max_inf, step)
        colors = RangeCreator.full_cream_color_ramp(len(bounds), start_hue, end_hue, hex_notation=True)
        rules = []
        for i in range(len(bounds)):
            #print(f'{colors[i]}, {bounds[i]})
            lower = bounds[i][0]
            if lower == 0:
                lower_string = '0'  # have to check this else we loose 0 or 0.0 ...
            else:
                lower_string = f'{lower:.3f}'.strip('0')
            upper = bounds[i][1]
            upper_string = f'{upper:.3f}'.strip('0')
            rule = RangeCreator.SLD_RULE_TEMPLATE.format(
                lower_boundary=lower,
                upper_boundary=upper,
                title=f'{lower_string} - {upper_string}',
                abstract=f'{lower_string} - {upper_string}',
                fill=colors[i])
            rules.insert(0, rule)
        return RangeCreator.SLD_TEMPLATE.format(rules=''.join(rules))

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
    # Range set, either logarithmic
    #print(RangeCreator.create_log_range_set(-1, 1, True, True))
    # or normal with step size defined
    #print(RangeCreator.create_range_set(0.23, 8, True))
    #print(RangeCreator.create_range_set(0.23, 8, step=3))
    #print(RangeCreator.create_rule_set())
    #print(RangeCreator.full_cream_color_ramp())
    #print(RangeCreator.create_log_sld(-1, 1, True, True))
    #print(RangeCreator.create_sld())
    #print(RangeCreator.create_range_set(0, 23.833333, step=(23.833333/10)))
    print(RangeCreator.create_sld(0, 23.833333, step=(23.833333/10)))
    #print(RangeCreator.create_sld(0.23, 8))
    #print(RangeCreator.create_sld(0.23, 8, step=3))

