<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis labelsEnabled="0" simplifyMaxScale="1" styleCategories="AllStyleCategories" simplifyDrawingTol="1" readOnly="0" minScale="100000000" version="3.13.0-Master" simplifyLocal="1" simplifyAlgorithm="0" maxScale="100000" hasScaleBasedVisibilityFlag="0" simplifyDrawingHints="0">
  <flags>
    <Identifiable>1</Identifiable>
    <Removable>1</Removable>
    <Searchable>1</Searchable>
  </flags>
  <renderer-v2 type="RuleRenderer" symbollevels="0" forceraster="0" enableorderby="1">
    <rules key="{e7991823-286e-4757-abcb-af6991a87fb7}">
      <rule label="Other Units" symbol="0" key="{b963d1de-6b64-4ac0-a0ce-627f2d540007}" description="Abstract" filter="(upper(&quot;unit&quot;) != 'NSV/H' and upper(&quot;unit&quot;) != 'USV/H')"/>
      <rule label="&lt;= 1E-1 µSv/h" symbol="1" key="{46d02429-d5ec-4fa0-964f-992313bf794f}" description="Abstract" filter="(upper(&quot;unit&quot;) = 'NSV/H' or upper(&quot;unit&quot;) = 'USV/H') and valuemicrosvh &lt;= 0.1"/>
      <rule label="1E-1 - 1 µSv/h" symbol="2" key="{0d506bed-7e29-4951-8dd6-950f7450eec1}" description="Abstract" filter="(upper(&quot;unit&quot;) = 'NSV/H' or upper(&quot;unit&quot;) = 'USV/H') and valuemicrosvh >= 0.1 AND valuemicrosvh &lt;= 1"/>
      <rule label="1 - 10 µSv/h" symbol="3" key="{8071164e-e3dc-4aab-86ea-e5bf80fb8a64}" description="Abstract" filter="(upper(&quot;unit&quot;) = 'NSV/H' or upper(&quot;unit&quot;) = 'USV/H') and valuemicrosvh >= 1 AND valuemicrosvh &lt;= 10"/>
      <rule label="10 - 100 µSv/h" symbol="4" key="{6763d8b5-1b32-4621-a388-498ec613aba3}" description="Abstract" filter="(upper(&quot;unit&quot;) = 'NSV/H' or upper(&quot;unit&quot;) = 'USV/H') and valuemicrosvh >= 10 AND valuemicrosvh &lt;= 100"/>
      <rule label="100 - 1000 µSv/h" symbol="5" key="{41bc24bd-294c-4818-ae41-17744878653f}" description="Abstract" filter="(upper(&quot;unit&quot;) = 'NSV/H' or upper(&quot;unit&quot;) = 'USV/H') and valuemicrosvh >= 100 AND valuemicrosvh &lt;= 1000"/>
      <rule label="1000 - 10000 µSv/h" symbol="6" key="{a26143cf-f0d8-4a5c-8ebb-e31e5d3ece27}" description="Abstract" filter="(upper(&quot;unit&quot;) = 'NSV/H' or upper(&quot;unit&quot;) = 'USV/H') and valuemicrosvh >= 1000 AND valuemicrosvh &lt;= 10000"/>
      <rule label="10000 - 100000 µSv/h" symbol="7" key="{dc24e19b-9919-4eed-9b5b-d5a7b3e6d3f7}" description="Abstract" filter="(upper(&quot;unit&quot;) = 'NSV/H' or upper(&quot;unit&quot;) = 'USV/H') and valuemicrosvh >= 10000 AND valuemicrosvh &lt;= 100000"/>
      <rule label="100000 - 1000000 µSv/h" symbol="8" key="{b2906596-36e6-4582-b813-885480ddf6ab}" description="Abstract" filter="(upper(&quot;unit&quot;) = 'NSV/H' or upper(&quot;unit&quot;) = 'USV/H') and valuemicrosvh >= 100000 AND valuemicrosvh &lt;= 1000000"/>
      <rule label="1000000 - 10000000 µSv/h" symbol="9" key="{4147d8ff-4b6e-4dfe-a935-474d1c1f9572}" description="Abstract" filter="(upper(&quot;unit&quot;) = 'NSV/H' or upper(&quot;unit&quot;) = 'USV/H') and valuemicrosvh >= 1000000 AND valuemicrosvh &lt;= 10000000"/>
      <rule label=">10000000 µSv/h" symbol="10" key="{54a5d065-9ab5-4c17-ae53-6686d5b0a354}" description="Abstract" filter="(upper(&quot;unit&quot;) = 'NSV/H' or upper(&quot;unit&quot;) = 'USV/H') and valuemicrosvh >= 10000000"/>
    </rules>
    <symbols>
      <symbol alpha="0.486275" type="marker" name="0" force_rhr="0" clip_to_extent="1">
        <layer class="SimpleMarker" pass="0" enabled="1" locked="0">
          <prop v="0" k="angle"/>
          <prop v="166,206,227,255" k="color"/>
          <prop v="1" k="horizontal_anchor_point"/>
          <prop v="bevel" k="joinstyle"/>
          <prop v="diamond" k="name"/>
          <prop v="0,0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="0,0,0,255" k="outline_color"/>
          <prop v="solid" k="outline_style"/>
          <prop v="0" k="outline_width"/>
          <prop v="3x:0,0,0,0,0,0" k="outline_width_map_unit_scale"/>
          <prop v="MM" k="outline_width_unit"/>
          <prop v="diameter" k="scale_method"/>
          <prop v="6" k="size"/>
          <prop v="3x:0,0,0,0,0,0" k="size_map_unit_scale"/>
          <prop v="MM" k="size_unit"/>
          <prop v="1" k="vertical_anchor_point"/>
          <data_defined_properties>
            <Option type="Map">
              <Option type="QString" value="" name="name"/>
              <Option type="Map" name="properties">
                <Option type="Map" name="angle">
                  <Option type="bool" value="true" name="active"/>
                  <Option type="QString" value="rand( 0, 18)*20" name="expression"/>
                  <Option type="int" value="3" name="type"/>
                </Option>
                <Option type="Map" name="offset">
                  <Option type="bool" value="false" name="active"/>
                  <Option type="QString" value="'' || rand( -2, 2) || ',' || rand( -2, 2)" name="expression"/>
                  <Option type="int" value="3" name="type"/>
                </Option>
              </Option>
              <Option type="QString" value="collection" name="type"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol alpha="1" type="marker" name="1" force_rhr="0" clip_to_extent="1">
        <layer class="SimpleMarker" pass="1" enabled="1" locked="0">
          <prop v="0" k="angle"/>
          <prop v="0,0,255,191" k="color"/>
          <prop v="1" k="horizontal_anchor_point"/>
          <prop v="bevel" k="joinstyle"/>
          <prop v="diamond" k="name"/>
          <prop v="0,0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="0,0,0,255" k="outline_color"/>
          <prop v="solid" k="outline_style"/>
          <prop v="0" k="outline_width"/>
          <prop v="3x:0,0,0,0,0,0" k="outline_width_map_unit_scale"/>
          <prop v="MM" k="outline_width_unit"/>
          <prop v="diameter" k="scale_method"/>
          <prop v="3" k="size"/>
          <prop v="3x:0,0,0,0,0,0" k="size_map_unit_scale"/>
          <prop v="MM" k="size_unit"/>
          <prop v="1" k="vertical_anchor_point"/>
          <data_defined_properties>
            <Option type="Map">
              <Option type="QString" value="" name="name"/>
              <Option type="Map" name="properties">
                <Option type="Map" name="offset">
                  <Option type="bool" value="false" name="active"/>
                  <Option type="QString" value="'' || rand( -1, 1) || ',' || rand( -1, 1)" name="expression"/>
                  <Option type="int" value="3" name="type"/>
                </Option>
              </Option>
              <Option type="QString" value="collection" name="type"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol alpha="1" type="marker" name="10" force_rhr="0" clip_to_extent="1">
        <layer class="SimpleMarker" pass="1" enabled="1" locked="0">
          <prop v="0" k="angle"/>
          <prop v="255,0,0,191" k="color"/>
          <prop v="1" k="horizontal_anchor_point"/>
          <prop v="bevel" k="joinstyle"/>
          <prop v="diamond" k="name"/>
          <prop v="0,0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="0,0,0,255" k="outline_color"/>
          <prop v="solid" k="outline_style"/>
          <prop v="0" k="outline_width"/>
          <prop v="3x:0,0,0,0,0,0" k="outline_width_map_unit_scale"/>
          <prop v="MM" k="outline_width_unit"/>
          <prop v="diameter" k="scale_method"/>
          <prop v="3" k="size"/>
          <prop v="3x:0,0,0,0,0,0" k="size_map_unit_scale"/>
          <prop v="MM" k="size_unit"/>
          <prop v="1" k="vertical_anchor_point"/>
          <data_defined_properties>
            <Option type="Map">
              <Option type="QString" value="" name="name"/>
              <Option type="Map" name="properties">
                <Option type="Map" name="offset">
                  <Option type="bool" value="false" name="active"/>
                  <Option type="QString" value="'' || rand( -1, 1) || ',' || rand( -1, 1)" name="expression"/>
                  <Option type="int" value="3" name="type"/>
                </Option>
              </Option>
              <Option type="QString" value="collection" name="type"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol alpha="1" type="marker" name="2" force_rhr="0" clip_to_extent="1">
        <layer class="SimpleMarker" pass="1" enabled="1" locked="0">
          <prop v="0" k="angle"/>
          <prop v="54,97,255,191" k="color"/>
          <prop v="1" k="horizontal_anchor_point"/>
          <prop v="bevel" k="joinstyle"/>
          <prop v="diamond" k="name"/>
          <prop v="0,0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="0,0,0,255" k="outline_color"/>
          <prop v="solid" k="outline_style"/>
          <prop v="0" k="outline_width"/>
          <prop v="3x:0,0,0,0,0,0" k="outline_width_map_unit_scale"/>
          <prop v="MM" k="outline_width_unit"/>
          <prop v="diameter" k="scale_method"/>
          <prop v="3" k="size"/>
          <prop v="3x:0,0,0,0,0,0" k="size_map_unit_scale"/>
          <prop v="MM" k="size_unit"/>
          <prop v="1" k="vertical_anchor_point"/>
          <data_defined_properties>
            <Option type="Map">
              <Option type="QString" value="" name="name"/>
              <Option type="Map" name="properties">
                <Option type="Map" name="offset">
                  <Option type="bool" value="false" name="active"/>
                  <Option type="QString" value="'' || rand( -1, 1) || ',' || rand( -1, 1)" name="expression"/>
                  <Option type="int" value="3" name="type"/>
                </Option>
              </Option>
              <Option type="QString" value="collection" name="type"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol alpha="1" type="marker" name="3" force_rhr="0" clip_to_extent="1">
        <layer class="SimpleMarker" pass="1" enabled="1" locked="0">
          <prop v="0" k="angle"/>
          <prop v="56,172,255,191" k="color"/>
          <prop v="1" k="horizontal_anchor_point"/>
          <prop v="bevel" k="joinstyle"/>
          <prop v="diamond" k="name"/>
          <prop v="0,0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="0,0,0,255" k="outline_color"/>
          <prop v="solid" k="outline_style"/>
          <prop v="0" k="outline_width"/>
          <prop v="3x:0,0,0,0,0,0" k="outline_width_map_unit_scale"/>
          <prop v="MM" k="outline_width_unit"/>
          <prop v="diameter" k="scale_method"/>
          <prop v="3" k="size"/>
          <prop v="3x:0,0,0,0,0,0" k="size_map_unit_scale"/>
          <prop v="MM" k="size_unit"/>
          <prop v="1" k="vertical_anchor_point"/>
          <data_defined_properties>
            <Option type="Map">
              <Option type="QString" value="" name="name"/>
              <Option type="Map" name="properties">
                <Option type="Map" name="offset">
                  <Option type="bool" value="false" name="active"/>
                  <Option type="QString" value="'' || rand( -1, 1) || ',' || rand( -1, 1)" name="expression"/>
                  <Option type="int" value="3" name="type"/>
                </Option>
              </Option>
              <Option type="QString" value="collection" name="type"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol alpha="1" type="marker" name="4" force_rhr="0" clip_to_extent="1">
        <layer class="SimpleMarker" pass="1" enabled="1" locked="0">
          <prop v="0" k="angle"/>
          <prop v="0,255,255,191" k="color"/>
          <prop v="1" k="horizontal_anchor_point"/>
          <prop v="bevel" k="joinstyle"/>
          <prop v="diamond" k="name"/>
          <prop v="0,0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="0,0,0,255" k="outline_color"/>
          <prop v="solid" k="outline_style"/>
          <prop v="0" k="outline_width"/>
          <prop v="3x:0,0,0,0,0,0" k="outline_width_map_unit_scale"/>
          <prop v="MM" k="outline_width_unit"/>
          <prop v="diameter" k="scale_method"/>
          <prop v="3" k="size"/>
          <prop v="3x:0,0,0,0,0,0" k="size_map_unit_scale"/>
          <prop v="MM" k="size_unit"/>
          <prop v="1" k="vertical_anchor_point"/>
          <data_defined_properties>
            <Option type="Map">
              <Option type="QString" value="" name="name"/>
              <Option type="Map" name="properties">
                <Option type="Map" name="offset">
                  <Option type="bool" value="false" name="active"/>
                  <Option type="QString" value="'' || rand( -1, 1) || ',' || rand( -1, 1)" name="expression"/>
                  <Option type="int" value="3" name="type"/>
                </Option>
              </Option>
              <Option type="QString" value="collection" name="type"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol alpha="1" type="marker" name="5" force_rhr="0" clip_to_extent="1">
        <layer class="SimpleMarker" pass="1" enabled="1" locked="0">
          <prop v="0" k="angle"/>
          <prop v="145,255,180,191" k="color"/>
          <prop v="1" k="horizontal_anchor_point"/>
          <prop v="bevel" k="joinstyle"/>
          <prop v="diamond" k="name"/>
          <prop v="0,0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="0,0,0,255" k="outline_color"/>
          <prop v="solid" k="outline_style"/>
          <prop v="0" k="outline_width"/>
          <prop v="3x:0,0,0,0,0,0" k="outline_width_map_unit_scale"/>
          <prop v="MM" k="outline_width_unit"/>
          <prop v="diameter" k="scale_method"/>
          <prop v="3" k="size"/>
          <prop v="3x:0,0,0,0,0,0" k="size_map_unit_scale"/>
          <prop v="MM" k="size_unit"/>
          <prop v="1" k="vertical_anchor_point"/>
          <data_defined_properties>
            <Option type="Map">
              <Option type="QString" value="" name="name"/>
              <Option type="Map" name="properties">
                <Option type="Map" name="offset">
                  <Option type="bool" value="false" name="active"/>
                  <Option type="QString" value="'' || rand( -1, 1) || ',' || rand( -1, 1)" name="expression"/>
                  <Option type="int" value="3" name="type"/>
                </Option>
              </Option>
              <Option type="QString" value="collection" name="type"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol alpha="1" type="marker" name="6" force_rhr="0" clip_to_extent="1">
        <layer class="SimpleMarker" pass="1" enabled="1" locked="0">
          <prop v="0" k="angle"/>
          <prop v="210,255,105,191" k="color"/>
          <prop v="1" k="horizontal_anchor_point"/>
          <prop v="bevel" k="joinstyle"/>
          <prop v="diamond" k="name"/>
          <prop v="0,0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="0,0,0,255" k="outline_color"/>
          <prop v="solid" k="outline_style"/>
          <prop v="0" k="outline_width"/>
          <prop v="3x:0,0,0,0,0,0" k="outline_width_map_unit_scale"/>
          <prop v="MM" k="outline_width_unit"/>
          <prop v="diameter" k="scale_method"/>
          <prop v="3" k="size"/>
          <prop v="3x:0,0,0,0,0,0" k="size_map_unit_scale"/>
          <prop v="MM" k="size_unit"/>
          <prop v="1" k="vertical_anchor_point"/>
          <data_defined_properties>
            <Option type="Map">
              <Option type="QString" value="" name="name"/>
              <Option type="Map" name="properties">
                <Option type="Map" name="offset">
                  <Option type="bool" value="false" name="active"/>
                  <Option type="QString" value="'' || rand( -1, 1) || ',' || rand( -1, 1)" name="expression"/>
                  <Option type="int" value="3" name="type"/>
                </Option>
              </Option>
              <Option type="QString" value="collection" name="type"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol alpha="1" type="marker" name="7" force_rhr="0" clip_to_extent="1">
        <layer class="SimpleMarker" pass="1" enabled="1" locked="0">
          <prop v="0" k="angle"/>
          <prop v="255,255,0,191" k="color"/>
          <prop v="1" k="horizontal_anchor_point"/>
          <prop v="bevel" k="joinstyle"/>
          <prop v="diamond" k="name"/>
          <prop v="0,0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="0,0,0,255" k="outline_color"/>
          <prop v="solid" k="outline_style"/>
          <prop v="0" k="outline_width"/>
          <prop v="3x:0,0,0,0,0,0" k="outline_width_map_unit_scale"/>
          <prop v="MM" k="outline_width_unit"/>
          <prop v="diameter" k="scale_method"/>
          <prop v="3" k="size"/>
          <prop v="3x:0,0,0,0,0,0" k="size_map_unit_scale"/>
          <prop v="MM" k="size_unit"/>
          <prop v="1" k="vertical_anchor_point"/>
          <data_defined_properties>
            <Option type="Map">
              <Option type="QString" value="" name="name"/>
              <Option type="Map" name="properties">
                <Option type="Map" name="offset">
                  <Option type="bool" value="false" name="active"/>
                  <Option type="QString" value="'' || rand( -1, 1) || ',' || rand( -1, 1)" name="expression"/>
                  <Option type="int" value="3" name="type"/>
                </Option>
              </Option>
              <Option type="QString" value="collection" name="type"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol alpha="1" type="marker" name="8" force_rhr="0" clip_to_extent="1">
        <layer class="SimpleMarker" pass="1" enabled="1" locked="0">
          <prop v="0" k="angle"/>
          <prop v="255,183,0,191" k="color"/>
          <prop v="1" k="horizontal_anchor_point"/>
          <prop v="bevel" k="joinstyle"/>
          <prop v="diamond" k="name"/>
          <prop v="0,0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="0,0,0,255" k="outline_color"/>
          <prop v="solid" k="outline_style"/>
          <prop v="0" k="outline_width"/>
          <prop v="3x:0,0,0,0,0,0" k="outline_width_map_unit_scale"/>
          <prop v="MM" k="outline_width_unit"/>
          <prop v="diameter" k="scale_method"/>
          <prop v="3" k="size"/>
          <prop v="3x:0,0,0,0,0,0" k="size_map_unit_scale"/>
          <prop v="MM" k="size_unit"/>
          <prop v="1" k="vertical_anchor_point"/>
          <data_defined_properties>
            <Option type="Map">
              <Option type="QString" value="" name="name"/>
              <Option type="Map" name="properties">
                <Option type="Map" name="offset">
                  <Option type="bool" value="false" name="active"/>
                  <Option type="QString" value="'' || rand( -1, 1) || ',' || rand( -1, 1)" name="expression"/>
                  <Option type="int" value="3" name="type"/>
                </Option>
              </Option>
              <Option type="QString" value="collection" name="type"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol alpha="1" type="marker" name="9" force_rhr="0" clip_to_extent="1">
        <layer class="SimpleMarker" pass="1" enabled="1" locked="0">
          <prop v="0" k="angle"/>
          <prop v="255,111,0,191" k="color"/>
          <prop v="1" k="horizontal_anchor_point"/>
          <prop v="bevel" k="joinstyle"/>
          <prop v="diamond" k="name"/>
          <prop v="0,0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="0,0,0,255" k="outline_color"/>
          <prop v="solid" k="outline_style"/>
          <prop v="0" k="outline_width"/>
          <prop v="3x:0,0,0,0,0,0" k="outline_width_map_unit_scale"/>
          <prop v="MM" k="outline_width_unit"/>
          <prop v="diameter" k="scale_method"/>
          <prop v="3" k="size"/>
          <prop v="3x:0,0,0,0,0,0" k="size_map_unit_scale"/>
          <prop v="MM" k="size_unit"/>
          <prop v="1" k="vertical_anchor_point"/>
          <data_defined_properties>
            <Option type="Map">
              <Option type="QString" value="" name="name"/>
              <Option type="Map" name="properties">
                <Option type="Map" name="offset">
                  <Option type="bool" value="false" name="active"/>
                  <Option type="QString" value="'' || rand( -1, 1) || ',' || rand( -1, 1)" name="expression"/>
                  <Option type="int" value="3" name="type"/>
                </Option>
              </Option>
              <Option type="QString" value="collection" name="type"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
    </symbols>
  </renderer-v2>
  <customproperties>
    <property key="dualview/previewExpressions">
      <value>COALESCE("Measurements", '&lt;NULL>')</value>
    </property>
    <property value="0" key="embeddedWidgets/count"/>
    <property key="variableNames"/>
    <property key="variableValues"/>
  </customproperties>
  <blendMode>0</blendMode>
  <featureBlendMode>0</featureBlendMode>
  <layerOpacity>1</layerOpacity>
  <LinearlyInterpolatedDiagramRenderer lowerWidth="0" upperHeight="50" classificationAttributeExpression="" upperWidth="50" upperValue="0" lowerHeight="0" diagramType="Histogram" lowerValue="0" attributeLegend="1">
    <DiagramCategory sizeScale="3x:0,0,0,0,0,0" lineSizeType="MM" spacing="0" opacity="1" diagramOrientation="Up" sizeType="MM" penColor="#000000" penAlpha="255" barWidth="5" spacingUnitScale="3x:0,0,0,0,0,0" rotationOffset="270" maxScaleDenominator="1e+08" showAxis="0" scaleDependency="Area" direction="1" labelPlacementMethod="XHeight" minScaleDenominator="100000" lineSizeScale="3x:0,0,0,0,0,0" backgroundAlpha="255" spacingUnit="MM" height="15" backgroundColor="#ffffff" minimumSize="0" width="15" enabled="0" penWidth="0" scaleBasedVisibility="0">
      <fontProperties style="" description="Cantarell,11,-1,5,50,0,0,0,0,0"/>
      <attribute label="" field="" color="#000000"/>
      <axisSymbol>
        <symbol alpha="1" type="line" name="" force_rhr="0" clip_to_extent="1">
          <layer class="SimpleLine" pass="0" enabled="1" locked="0">
            <prop v="square" k="capstyle"/>
            <prop v="5;2" k="customdash"/>
            <prop v="3x:0,0,0,0,0,0" k="customdash_map_unit_scale"/>
            <prop v="MM" k="customdash_unit"/>
            <prop v="0" k="draw_inside_polygon"/>
            <prop v="bevel" k="joinstyle"/>
            <prop v="35,35,35,255" k="line_color"/>
            <prop v="solid" k="line_style"/>
            <prop v="0.26" k="line_width"/>
            <prop v="MM" k="line_width_unit"/>
            <prop v="0" k="offset"/>
            <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
            <prop v="MM" k="offset_unit"/>
            <prop v="0" k="ring_filter"/>
            <prop v="0" k="use_custom_dash"/>
            <prop v="3x:0,0,0,0,0,0" k="width_map_unit_scale"/>
            <data_defined_properties>
              <Option type="Map">
                <Option type="QString" value="" name="name"/>
                <Option name="properties"/>
                <Option type="QString" value="collection" name="type"/>
              </Option>
            </data_defined_properties>
          </layer>
        </symbol>
      </axisSymbol>
    </DiagramCategory>
  </LinearlyInterpolatedDiagramRenderer>
  <DiagramLayerSettings obstacle="0" priority="0" placement="0" linePlacementFlags="2" zIndex="0" dist="0" showAll="1">
    <properties>
      <Option type="Map">
        <Option type="QString" value="" name="name"/>
        <Option type="Map" name="properties">
          <Option type="Map" name="show">
            <Option type="bool" value="true" name="active"/>
            <Option type="QString" value="gml_id" name="field"/>
            <Option type="int" value="2" name="type"/>
          </Option>
        </Option>
        <Option type="QString" value="collection" name="type"/>
      </Option>
    </properties>
  </DiagramLayerSettings>
  <geometryOptions geometryPrecision="0" removeDuplicateNodes="0">
    <activeChecks/>
    <checkConfiguration/>
  </geometryOptions>
  <referencedLayers/>
  <referencingLayers/>
  <fieldConfiguration>
    <field name="gml_id">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="startTime">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="endTime">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="quantity">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="substance">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="unit">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="value">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="time">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="info">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="device">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="valuemicrosvh">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
  </fieldConfiguration>
  <aliases>
    <alias field="gml_id" index="0" name=""/>
    <alias field="startTime" index="1" name=""/>
    <alias field="endTime" index="2" name=""/>
    <alias field="quantity" index="3" name=""/>
    <alias field="substance" index="4" name=""/>
    <alias field="unit" index="5" name=""/>
    <alias field="value" index="6" name=""/>
    <alias field="time" index="7" name=""/>
    <alias field="info" index="8" name=""/>
    <alias field="device" index="9" name=""/>
    <alias field="valuemicrosvh" index="10" name=""/>
  </aliases>
  <excludeAttributesWMS/>
  <excludeAttributesWFS/>
  <defaults>
    <default expression="" field="gml_id" applyOnUpdate="0"/>
    <default expression="" field="startTime" applyOnUpdate="0"/>
    <default expression="" field="endTime" applyOnUpdate="0"/>
    <default expression="" field="quantity" applyOnUpdate="0"/>
    <default expression="" field="substance" applyOnUpdate="0"/>
    <default expression="" field="unit" applyOnUpdate="0"/>
    <default expression="" field="value" applyOnUpdate="0"/>
    <default expression="" field="time" applyOnUpdate="0"/>
    <default expression="" field="info" applyOnUpdate="0"/>
    <default expression="" field="device" applyOnUpdate="0"/>
    <default expression="" field="valuemicrosvh" applyOnUpdate="0"/>
  </defaults>
  <constraints>
    <constraint unique_strength="0" exp_strength="0" field="gml_id" constraints="0" notnull_strength="0"/>
    <constraint unique_strength="0" exp_strength="0" field="startTime" constraints="0" notnull_strength="0"/>
    <constraint unique_strength="0" exp_strength="0" field="endTime" constraints="0" notnull_strength="0"/>
    <constraint unique_strength="0" exp_strength="0" field="quantity" constraints="0" notnull_strength="0"/>
    <constraint unique_strength="0" exp_strength="0" field="substance" constraints="0" notnull_strength="0"/>
    <constraint unique_strength="0" exp_strength="0" field="unit" constraints="0" notnull_strength="0"/>
    <constraint unique_strength="0" exp_strength="0" field="value" constraints="0" notnull_strength="0"/>
    <constraint unique_strength="0" exp_strength="0" field="time" constraints="0" notnull_strength="0"/>
    <constraint unique_strength="0" exp_strength="0" field="info" constraints="0" notnull_strength="0"/>
    <constraint unique_strength="0" exp_strength="0" field="device" constraints="0" notnull_strength="0"/>
    <constraint unique_strength="0" exp_strength="0" field="valuemicrosvh" constraints="0" notnull_strength="0"/>
  </constraints>
  <constraintExpressions>
    <constraint desc="" field="gml_id" exp=""/>
    <constraint desc="" field="startTime" exp=""/>
    <constraint desc="" field="endTime" exp=""/>
    <constraint desc="" field="quantity" exp=""/>
    <constraint desc="" field="substance" exp=""/>
    <constraint desc="" field="unit" exp=""/>
    <constraint desc="" field="value" exp=""/>
    <constraint desc="" field="time" exp=""/>
    <constraint desc="" field="info" exp=""/>
    <constraint desc="" field="device" exp=""/>
    <constraint desc="" field="valuemicrosvh" exp=""/>
  </constraintExpressions>
  <expressionfields/>
  <attributeactions>
    <defaultAction value="{00000000-0000-0000-0000-000000000000}" key="Canvas"/>
  </attributeactions>
  <attributetableconfig sortOrder="0" actionWidgetStyle="dropDown" sortExpression="&quot;gml_id&quot;">
    <columns>
      <column type="field" width="119" hidden="0" name="gml_id"/>
      <column type="field" width="201" hidden="0" name="startTime"/>
      <column type="field" width="212" hidden="0" name="endTime"/>
      <column type="field" width="-1" hidden="0" name="quantity"/>
      <column type="field" width="-1" hidden="0" name="substance"/>
      <column type="field" width="-1" hidden="0" name="unit"/>
      <column type="field" width="-1" hidden="0" name="value"/>
      <column type="field" width="-1" hidden="0" name="time"/>
      <column type="field" width="148" hidden="0" name="info"/>
      <column type="field" width="-1" hidden="0" name="device"/>
      <column type="field" width="-1" hidden="0" name="valuemicrosvh"/>
      <column type="actions" width="-1" hidden="1"/>
    </columns>
  </attributetableconfig>
  <conditionalstyles>
    <rowstyles/>
    <fieldstyles/>
  </conditionalstyles>
  <storedexpressions/>
  <editform tolerant="1">.</editform>
  <editforminit/>
  <editforminitcodesource>0</editforminitcodesource>
  <editforminitfilepath>.</editforminitfilepath>
  <editforminitcode><![CDATA[# -*- coding: utf-8 -*-
"""
QGIS forms can have a Python function that is called when the form is
opened.

Use this function to add extra logic to your forms.

Enter the name of the function in the "Python Init function"
field.
An example follows:
"""
from qgis.PyQt.QtWidgets import QWidget

def my_form_open(dialog, layer, feature):
	geom = feature.geometry()
	control = dialog.findChild(QWidget, "MyLineEdit")
]]></editforminitcode>
  <featformsuppress>0</featformsuppress>
  <editorlayout>generatedlayout</editorlayout>
  <editable>
    <field editable="1" name="device"/>
    <field editable="1" name="endTime"/>
    <field editable="1" name="gml_id"/>
    <field editable="1" name="info"/>
    <field editable="1" name="quantity"/>
    <field editable="1" name="startTime"/>
    <field editable="1" name="substance"/>
    <field editable="1" name="time"/>
    <field editable="1" name="unit"/>
    <field editable="1" name="value"/>
    <field editable="1" name="valuemicrosvh"/>
  </editable>
  <labelOnTop>
    <field labelOnTop="0" name="device"/>
    <field labelOnTop="0" name="endTime"/>
    <field labelOnTop="0" name="gml_id"/>
    <field labelOnTop="0" name="info"/>
    <field labelOnTop="0" name="quantity"/>
    <field labelOnTop="0" name="startTime"/>
    <field labelOnTop="0" name="substance"/>
    <field labelOnTop="0" name="time"/>
    <field labelOnTop="0" name="unit"/>
    <field labelOnTop="0" name="value"/>
    <field labelOnTop="0" name="valuemicrosvh"/>
  </labelOnTop>
  <dataDefinedFieldProperties/>
  <widgets/>
  <previewExpression>COALESCE("Measurements", '&lt;NULL>')</previewExpression>
  <mapTip>[% measurement_values()%]</mapTip>
  <layerGeometryType>0</layerGeometryType>
</qgis>
