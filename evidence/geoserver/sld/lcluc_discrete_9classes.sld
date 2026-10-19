<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor xmlns="http://www.opengis.net/sld" xmlns:ogc="http://www.opengis.net/ogc" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd" version="1.0.0">
  <NamedLayer>
    <Name>lcluc_discrete_9classes</Name>
    <UserStyle>
      <Title>LCLUC 9-Class Discrete Land Cover Classification Style</Title>
      <Abstract>Authoritative discrete raster classification style for LCLUC 9 classes with transparent NoData and strict nearest-neighbor resampling.</Abstract>
      <FeatureTypeStyle>
        <Rule>
          <Name>Discrete9Classes</Name>
          <Title>9 Land Cover Classes</Title>
          <Abstract>Discrete integer classification mapping (0..8) and transparent nodata (255, 65535)</Abstract>
          <RasterSymbolizer>
            <Opacity>1.0</Opacity>
            <ColorMap type="values">
              <!-- Class 0: Water -->
              <ColorMapEntry color="#2563eb" quantity="0" label="Water" opacity="1.0"/>
              <!-- Class 1: Trees / Forest -->
              <ColorMapEntry color="#15803d" quantity="1" label="Trees" opacity="1.0"/>
              <!-- Class 2: Grassland -->
              <ColorMapEntry color="#84cc16" quantity="2" label="Grass" opacity="1.0"/>
              <!-- Class 3: Flooded vegetation / Wetland -->
              <ColorMapEntry color="#14b8a6" quantity="3" label="Flooded vegetation" opacity="1.0"/>
              <!-- Class 4: Crops -->
              <ColorMapEntry color="#eab308" quantity="4" label="Crops" opacity="1.0"/>
              <!-- Class 5: Shrub & scrub -->
              <ColorMapEntry color="#a16207" quantity="5" label="Shrub &amp; scrub" opacity="1.0"/>
              <!-- Class 6: Built area / Urban -->
              <ColorMapEntry color="#dc2626" quantity="6" label="Built area" opacity="1.0"/>
              <!-- Class 7: Bare ground / Rock -->
              <ColorMapEntry color="#a8a29e" quantity="7" label="Bare ground" opacity="1.0"/>
              <!-- Class 8: Snow & ice -->
              <ColorMapEntry color="#a5d8f3" quantity="8" label="Snow &amp; ice" opacity="1.0"/>
              <!-- NoData Entries: 255 (uint8 standard nodata) and 65535 (uint16 standard nodata) -->
              <ColorMapEntry color="#000000" quantity="255" label="NoData (uint8)" opacity="0.0"/>
              <ColorMapEntry color="#000000" quantity="65535" label="NoData (uint16)" opacity="0.0"/>
            </ColorMap>
            <!-- VendorOption enforcing Nearest Neighbor resampling in GeoServer WMS/GWC -->
            <VendorOption name="resampling">nearest</VendorOption>
          </RasterSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>
