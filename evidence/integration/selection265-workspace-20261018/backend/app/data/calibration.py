"""L2A 제품 XML의 실제 수치로 반사도 변환 메타데이터를 검증한다."""
import math
import xml.etree.ElementTree as ET

SOURCE = "https://sentiwiki.copernicus.eu/web/s2-products"
BAND_IDS = {"B01": "0", "B02": "1", "B03": "2", "B04": "3", "B05": "4", "B06": "5", "B07": "6", "B08": "7", "B8A": "8", "B09": "9", "B10": "10", "B11": "11", "B12": "12"}


def parse_product_calibration(raw, bands, processing_baseline=None):
    root = ET.fromstring(raw)
    nodes = list(root.iter())
    def tag(node):
        return node.tag.split("}")[-1]
    xml_baselines = [node.text for node in nodes if tag(node) == "PROCESSING_BASELINE" and node.text]
    product_uris = [node.text for node in nodes if tag(node) in ("PRODUCT_URI", "PRODUCT_URI_2A") and node.text and "MSIL2A" in node.text]
    baseline = xml_baselines[0] if xml_baselines else processing_baseline
    quant_values = [node.text for node in nodes if tag(node).endswith("BOA_QUANTIFICATION_VALUE") and node.text]
    offsets = {node.attrib.get("band_id"): node.text for node in nodes if tag(node) == "BOA_ADD_OFFSET"}
    report = {"verified": False, "baseline": baseline, "baseline_source": "product_xml" if xml_baselines else "STAC properties",
              "xml_product_uri": product_uris[0] if product_uris else None,
              "official_interpretation": SOURCE, "formula": "reflectance=(DN+BOA_ADD_OFFSET)/BOA_QUANTIFICATION_VALUE; DN0 excluded",
              "bands": {}, "scale_offset_applied_to_image": False}
    if not quant_values:
        return {**report, "reason": "제품XML에서BOA_QUANTIFICATION_VALUE를확인하지못함"}
    quant = float(quant_values[0])
    if not math.isfinite(quant) or quant <= 0:
        raise ValueError("유효한 BOA quantification 값이 아닙니다")
    try:
        pre04 = float(baseline) < 4
    except (TypeError, ValueError):
        pre04 = False
    for band in bands:
        identifier = BAND_IDS.get(band)
        if identifier in offsets:
            offset = float(offsets[identifier])
            basis = "explicit_product_XML_BOA_ADD_OFFSET"
        elif pre04:
            offset, basis = 0, "documented_pre04_no_radiometric_offset_rule"
        else:
            report["bands"][band] = {"verified": False, "reason": "PB04이후/미상제품의밴드offset누락"}
            continue
        if not math.isfinite(offset):
            raise ValueError("유효한 BOA offset이 아닙니다")
        report["bands"][band] = {"verified": True, "scale": 1 / quant, "offset": offset / quant,
                                 "quantification": quant, "dn_offset": offset, "offset_basis": basis}
    report["verified"] = bool(bands) and all(report["bands"][band]["verified"] for band in bands)
    return report
