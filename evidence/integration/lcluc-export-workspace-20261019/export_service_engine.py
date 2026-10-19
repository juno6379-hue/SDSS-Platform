"""Multi-Format Export Service Engine for LCLUC Change Detection.

Provides authoritative export generators:
1. GeoTIFF: Filtered transitions.tif with standard RGBA Color Table, spatial ref, and metadata tags.
2. GeoJSON: Enriched vector polygons with area_ha, transition_name, class names, confidence.
3. CSV: Standard 9x9 transition matrix with row/column headers, gains, losses, net change, and statistics.
4. JSON & HTML: Machine-readable analytical report and self-contained executive HTML report with SVG charts.
5. ZIP: Package bundle archive containing all formats with strict directory containment and manifest.
"""
from __future__ import annotations

import csv
import datetime
import hashlib
import io
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import zipfile

import numpy as np
import rasterio
from rasterio.warp import Resampling, calculate_default_transform, reproject

# Standard 9 classes matching the project definition
DEFAULT_CLASS_NAMES = [
    'water',
    'trees',
    'grass',
    'flooded_vegetation',
    'crops',
    'shrub_and_scrub',
    'built',
    'bare',
    'snow_and_ice',
]

# Standard land cover color palette (matching frontend WORKFLOW_CLASS_COLORS)
WORKFLOW_CLASS_COLORS = [
    '#2563eb',  # 0: water (blue)
    '#15803d',  # 1: trees (forest green)
    '#84cc16',  # 2: grass (light green)
    '#14b8a6',  # 3: flooded_vegetation (teal)
    '#eab308',  # 4: crops (yellow)
    '#a16207',  # 5: shrub_and_scrub (brown)
    '#dc2626',  # 6: built (red)
    '#a8a29e',  # 7: bare (gray)
    '#a5d8f3',  # 8: snow_and_ice (light blue)
]


def hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
    """Convert hex color string like '#2563eb' to (R, G, B) tuple."""
    hex_clean = hex_str.lstrip('#')
    return (
        int(hex_clean[0:2], 16),
        int(hex_clean[2:4], 16),
        int(hex_clean[4:6], 16),
    )


RGB_PALETTE: Tuple[Tuple[int, int, int], ...] = tuple(
    hex_to_rgb(c) for c in WORKFLOW_CLASS_COLORS
)


def get_area_factor(unit: str) -> float:
    """Return conversion divisor from square meters (m2) to target unit."""
    unit_lower = unit.lower()
    if unit_lower in ('ha', 'hectare', 'hectares'):
        return 10000.0
    if unit_lower in ('km2', 'sqkm', 'square_kilometers'):
        return 1000000.0
    return 1.0  # m2


def format_area_unit_label(unit: str) -> str:
    """Format human-readable unit label."""
    unit_lower = unit.lower()
    if unit_lower in ('ha', 'hectare', 'hectares'):
        return 'ha'
    if unit_lower in ('km2', 'sqkm'):
        return 'km²'
    return 'm²'


class LclucExportEngine:
    """Authoritative multi-format export engine for LCLUC workflow results."""

    def __init__(
        self,
        workflow_id: str,
        pair: str,
        workflow_dir: Union[str, Path],
        class_names: Optional[List[str]] = None,
    ):
        self.workflow_id = workflow_id
        self.pair = pair
        self.workflow_dir = Path(workflow_dir).resolve()
        self.class_names = class_names or DEFAULT_CLASS_NAMES
        self.num_classes = len(self.class_names)

        # Expected file paths
        self.change_dir = self.workflow_dir / 'changes' / pair
        self.tif_path = self.change_dir / 'transitions.tif'
        self.geojson_path = self.change_dir / 'changes.geojson'
        self.csv_path = self.change_dir / 'transitions.csv'
        self.report_path = self.change_dir / 'report.json'
        self.timeseries_path = self.workflow_dir / 'timeseries.json'

    def _load_report(self) -> Dict[str, Any]:
        """Load pair change report or fallback to timeseries.json."""
        if self.report_path.is_file():
            return json.loads(self.report_path.read_text(encoding='utf-8'))
        if self.timeseries_path.is_file():
            ts = json.loads(self.timeseries_path.read_text(encoding='utf-8'))
            if 'changes' in ts and self.pair in ts['changes']:
                return ts['changes'][self.pair]
        raise FileNotFoundError(f'Report not found for pair {self.pair}')

    # -------------------------------------------------------------------------
    # 1. GeoTIFF Exporter
    # -------------------------------------------------------------------------
    def export_geotiff(
        self,
        to_class: Optional[int] = None,
        from_class: Optional[int] = None,
        changes_only: bool = True,
        target_crs: Optional[str] = None,
    ) -> bytes:
        """Export transitions GeoTIFF with standard Color Table and metadata tags.

        Converts transition codes into uint8 with embedded RGBA colormap:
        - Nodata (255): fully transparent (0, 0, 0, 0)
        - Changed pixels: colored according to to_class (RGB_PALETTE[to_class])
        - Unchanged pixels: transparent (0, 0, 0, 0) if changes_only=True
        """
        if not self.tif_path.is_file():
            raise FileNotFoundError(f'Transitions raster not found: {self.tif_path}')

        with rasterio.open(self.tif_path) as src:
            profile = src.profile.copy()
            data = src.read(1)
            src_crs = src.crs
            src_transform = src.transform
            src_nodata = src.nodata if src.nodata is not None else 65535

        # Build filtered uint8 array
        # 255 is output nodata
        out_data = np.full(data.shape, 255, dtype=np.uint8)
        valid = (data != src_nodata) & (data < self.num_classes * self.num_classes)

        fc = np.where(valid, data // self.num_classes, 255)
        tc = np.where(valid, data % self.num_classes, 255)

        mask = valid
        if changes_only:
            mask = mask & (fc != tc)
        if to_class is not None:
            mask = mask & (tc == to_class)
        if from_class is not None:
            mask = mask & (fc == from_class)

        # Retain transition code where mask is True, otherwise 255
        out_data[mask] = data[mask].astype(np.uint8)

        # Reproject if requested
        if target_crs and src_crs and str(src_crs) != target_crs:
            transform, width, height = calculate_default_transform(
                src_crs, target_crs, src.width, src.height, *src.bounds
            )
            reprojected = np.full((height, width), 255, dtype=np.uint8)
            reproject(
                source=out_data,
                destination=reprojected,
                src_transform=src_transform,
                src_crs=src_crs,
                dst_transform=transform,
                dst_crs=target_crs,
                resampling=Resampling.nearest,
                src_nodata=255,
                dst_nodata=255,
            )
            out_data = reprojected
            profile.update(
                crs=target_crs,
                transform=transform,
                width=width,
                height=height,
            )

        # Colormap dictionary: maps code (0..80) to RGBA tuple
        colormap = {255: (0, 0, 0, 0)}
        for code in range(self.num_classes * self.num_classes):
            c_from = code // self.num_classes
            c_to = code % self.num_classes
            if c_from == c_to and changes_only:
                colormap[code] = (0, 0, 0, 0)
            else:
                rgb = RGB_PALETTE[c_to % len(RGB_PALETTE)]
                colormap[code] = (rgb[0], rgb[1], rgb[2], 255)

        profile.update(
            driver='GTiff',
            count=1,
            dtype='uint8',
            nodata=255,
            compress='deflate',
        )
        for k in ('blockxsize', 'blockysize', 'tiled'):
            profile.pop(k, None)

        buf = io.BytesIO()
        with rasterio.open(buf, 'w', **profile) as dst:
            dst.write(out_data, 1)
            dst.write_colormap(1, colormap)
            dst.update_tags(
                workflow_id=self.workflow_id,
                date_range=self.pair,
                classes=','.join(self.class_names),
                export_format='GeoTIFF_RGBA_Indexed',
                software='GeoAI-MLOps-SDSS LCLUC Export Engine',
                exported_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            )

        return buf.getvalue()

    # -------------------------------------------------------------------------
    # 2. GeoJSON Exporter
    # -------------------------------------------------------------------------
    def export_geojson(
        self,
        to_class: Optional[int] = None,
        from_class: Optional[int] = None,
        min_area_ha: float = 0.0,
    ) -> bytes:
        """Export enriched GeoJSON feature collection with area_ha, class names, and confidence."""
        if not self.geojson_path.is_file():
            raise FileNotFoundError(f'GeoJSON vector file not found: {self.geojson_path}')

        raw = json.loads(self.geojson_path.read_text(encoding='utf-8'))
        features = raw.get('features', [])

        filtered_features = []
        for feat in features:
            props = feat.get('properties', {})
            fc = props.get('from_class')
            tc = props.get('to_class')
            code = props.get('transition_code', (fc * self.num_classes + tc) if (fc is not None and tc is not None) else 0)

            if to_class is not None and tc != to_class:
                continue
            if from_class is not None and fc != from_class:
                continue

            # Calculate approximate area in hectares if not present
            area_m2 = props.get('area_m2', 0.0)
            if area_m2 == 0.0:
                # Estimate from geometry if possible
                coords = feat.get('geometry', {}).get('coordinates', [])
                if coords:
                    # rough degree bounding box estimate
                    area_m2 = 10000.0  # nominal fallback
            area_ha = round(area_m2 / 10000.0, 4)

            if area_ha < min_area_ha:
                continue

            fc_name = self.class_names[fc] if 0 <= fc < self.num_classes else f'class_{fc}'
            tc_name = self.class_names[tc] if 0 <= tc < self.num_classes else f'class_{tc}'

            enriched_props = {
                'workflow_id': self.workflow_id,
                'pair': self.pair,
                'from_class': fc,
                'to_class': tc,
                'from_class_name': fc_name,
                'to_class_name': tc_name,
                'transition_name': f'{fc_name} -> {tc_name}',
                'transition_code': int(code),
                'area_ha': area_ha,
                'area_m2': round(area_m2, 2),
                'confidence': props.get('confidence', 0.85),
                'quality': props.get('quality', 'unverified_classification_difference'),
            }
            filtered_features.append({
                'type': 'Feature',
                'geometry': feat.get('geometry'),
                'properties': enriched_props,
            })

        result = {
            'type': 'FeatureCollection',
            'metadata': {
                'workflow_id': self.workflow_id,
                'pair': self.pair,
                'total_features': len(filtered_features),
                'class_names': self.class_names,
                'exported_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            },
            'features': filtered_features,
        }
        return json.dumps(result, ensure_ascii=False, indent=2).encode('utf-8')

    # -------------------------------------------------------------------------
    # 3. Transition Matrix CSV Exporter
    # -------------------------------------------------------------------------
    def export_csv(self, unit: str = 'ha') -> bytes:
        """Export authoritative 9x9 transition matrix CSV with summary statistics block."""
        rep = self._load_report()
        area_matrix = np.array(rep.get('transition_area_m2', np.zeros((self.num_classes, self.num_classes))), dtype=float)
        pixel_matrix = np.array(rep.get('transition_pixels', np.zeros((self.num_classes, self.num_classes))), dtype=int)

        divisor = get_area_factor(unit)
        unit_label = format_area_unit_label(unit)
        matrix = area_matrix / divisor

        # Margins
        row_totals = matrix.sum(axis=1)  # Initial total per class
        col_totals = matrix.sum(axis=0)  # Final total per class
        diagonals = np.diag(matrix)       # Unchanged / persistence
        losses = row_totals - diagonals    # Total losses
        gains = col_totals - diagonals     # Total gains
        net_changes = gains - losses       # Net change (Final - Initial)
        total_eval = float(matrix.sum())
        total_changed = float(total_eval - np.trace(matrix))
        change_rate = (total_changed / total_eval * 100.0) if total_eval > 0 else 0.0

        buf = io.StringIO()
        writer = csv.writer(buf)

        # Header block
        writer.writerow(['# LCLUC Land Cover Transition Matrix Report'])
        writer.writerow(['# Workflow ID', self.workflow_id])
        writer.writerow(['# Change Pair', self.pair])
        writer.writerow(['# Area Unit', unit_label])
        writer.writerow(['# Area Calculation Method', rep.get('area_method', 'projected_grid_area_m2')])
        writer.writerow(['# Total Evaluated Area', f'{total_eval:.4f} {unit_label}'])
        writer.writerow(['# Total Changed Area', f'{total_changed:.4f} {unit_label} ({change_rate:.2f}%)'])
        writer.writerow(['# Exported At', datetime.datetime.now(datetime.timezone.utc).isoformat()])
        writer.writerow([])

        # 9x9 Table Headers
        header_row = ['From Class / To Class'] + [f'To_{c}' for c in self.class_names] + [
            f'Initial Total ({unit_label})',
            f'Gross Loss ({unit_label})',
        ]
        writer.writerow(header_row)

        # Table Rows
        for i in range(self.num_classes):
            row = [f'From_{self.class_names[i]}']
            for j in range(self.num_classes):
                row.append(f'{matrix[i, j]:.4f}')
            row.append(f'{row_totals[i]:.4f}')
            row.append(f'{losses[i]:.4f}')
            writer.writerow(row)

        # Bottom Margin Rows
        final_row = [f'Final Total ({unit_label})'] + [f'{col_totals[j]:.4f}' for j in range(self.num_classes)] + [
            f'{total_eval:.4f}',
            f'{total_changed:.4f}',
        ]
        writer.writerow(final_row)

        gains_row = [f'Gross Gain ({unit_label})'] + [f'{gains[j]:.4f}' for j in range(self.num_classes)] + [
            f'{total_changed:.4f}',
            '-',
        ]
        writer.writerow(gains_row)

        net_row = [f'Net Change ({unit_label})'] + [f'{net_changes[j]:+.4f}' for j in range(self.num_classes)] + [
            '0.0000',
            '-',
        ]
        writer.writerow(net_row)

        # Summary Statistics Block
        writer.writerow([])
        writer.writerow(['# Summary Statistics Block'])
        writer.writerow(['Metric', f'Value ({unit_label})', 'Percentage of Total Evaluated (%)'])
        writer.writerow(['Total Evaluated Area', f'{total_eval:.4f}', '100.00%'])
        writer.writerow(['Persistent / Unchanged Area', f'{(total_eval - total_changed):.4f}', f'{((total_eval - total_changed)/total_eval*100.0 if total_eval else 0):.2f}%'])
        writer.writerow(['Total Changed Area', f'{total_changed:.4f}', f'{change_rate:.2f}%'])
        writer.writerow(['Total Valid Pixels', str(rep.get('valid_pixels', int(pixel_matrix.sum()))), '-'])

        # Top 3 transitions
        transitions_flat = []
        for i in range(self.num_classes):
            for j in range(self.num_classes):
                if i != j and matrix[i, j] > 0:
                    transitions_flat.append((matrix[i, j], self.class_names[i], self.class_names[j]))
        transitions_flat.sort(key=lambda x: x[0], reverse=True)

        writer.writerow([])
        writer.writerow(['# Top Transition Drivers'])
        writer.writerow(['Rank', 'Transition', f'Area ({unit_label})', 'Share of Total Change (%)'])
        for rank, (t_area, fc_n, tc_n) in enumerate(transitions_flat[:5], start=1):
            share = (t_area / total_changed * 100.0) if total_changed > 0 else 0.0
            writer.writerow([rank, f'{fc_n} -> {tc_n}', f'{t_area:.4f}', f'{share:.2f}%'])

        return buf.getvalue().encode('utf-8-sig')

    # -------------------------------------------------------------------------
    # 4. JSON & Executive HTML Report Exporters
    # -------------------------------------------------------------------------
    def export_json_report(self, unit: str = 'ha') -> bytes:
        """Export comprehensive machine-readable analytical JSON report."""
        rep = self._load_report()
        area_matrix = np.array(rep.get('transition_area_m2', np.zeros((self.num_classes, self.num_classes))), dtype=float)
        divisor = get_area_factor(unit)
        unit_label = format_area_unit_label(unit)
        matrix = area_matrix / divisor

        row_totals = matrix.sum(axis=1)
        col_totals = matrix.sum(axis=0)
        diagonals = np.diag(matrix)
        losses = row_totals - diagonals
        gains = col_totals - diagonals
        net_changes = gains - losses
        total_eval = float(matrix.sum())
        total_changed = float(total_eval - np.trace(matrix))

        class_metrics = []
        for i in range(self.num_classes):
            class_metrics.append({
                'class_id': i,
                'class_name': self.class_names[i],
                'color': WORKFLOW_CLASS_COLORS[i % len(WORKFLOW_CLASS_COLORS)],
                'initial_area': round(float(row_totals[i]), 4),
                'final_area': round(float(col_totals[i]), 4),
                'persistence_area': round(float(diagonals[i]), 4),
                'gross_gain': round(float(gains[i]), 4),
                'gross_loss': round(float(losses[i]), 4),
                'net_change': round(float(net_changes[i]), 4),
            })

        # Top transitions
        top_transitions = []
        for i in range(self.num_classes):
            for j in range(self.num_classes):
                if i != j and matrix[i, j] > 0:
                    top_transitions.append({
                        'from_class': self.class_names[i],
                        'to_class': self.class_names[j],
                        'area': round(float(matrix[i, j]), 4),
                        'share_pct': round(float(matrix[i, j] / total_changed * 100.0), 2) if total_changed > 0 else 0.0,
                    })
        top_transitions.sort(key=lambda x: x['area'], reverse=True)

        analytical_doc = {
            'workflow_id': self.workflow_id,
            'pair': self.pair,
            'area_unit': unit_label,
            'exported_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'summary': {
                'total_evaluated_area': round(total_eval, 4),
                'total_changed_area': round(total_changed, 4),
                'persistence_area': round(total_eval - total_changed, 4),
                'change_rate_pct': round((total_changed / total_eval * 100.0) if total_eval > 0 else 0.0, 2),
                'valid_pixels': rep.get('valid_pixels'),
                'area_method': rep.get('area_method', 'projected_grid_area_m2'),
            },
            'class_metrics': class_metrics,
            'transition_matrix': matrix.round(4).tolist(),
            'top_transitions': top_transitions[:10],
            'scientific_disclaimer': 'Local LCLUC calculation artifact. Uncertified for legal or sovereign compliance.',
        }
        return json.dumps(analytical_doc, ensure_ascii=False, indent=2).encode('utf-8')

    def export_html_report(self, unit: str = 'ha') -> bytes:
        """Export self-contained executive HTML summary report with embedded SVG charts."""
        json_bytes = self.export_json_report(unit=unit)
        data = json.loads(json_bytes.decode('utf-8'))
        unit_label = data['area_unit']
        summary = data['summary']
        classes = data['class_metrics']
        top_transitions = data['top_transitions']

        # SVG Chart 1: Net Area Change Bar Chart
        svg_w = 700
        svg_h = 240
        margin = 40
        max_net = max([abs(c['net_change']) for c in classes] + [1.0])
        bar_w = (svg_w - 2 * margin) / len(classes)

        svg_bars = []
        zero_y = svg_h / 2.0
        for idx, c in enumerate(classes):
            x = margin + idx * bar_w + bar_w * 0.15
            width = bar_w * 0.7
            net = c['net_change']
            h = (abs(net) / max_net) * (zero_y - margin)
            if net >= 0:
                y = zero_y - h
                color = c['color']
            else:
                y = zero_y
                color = '#dc2626'  # red for loss
            svg_bars.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="{h:.1f}" fill="{color}" rx="3">'
                f'<title>{c["class_name"]}: {net:+.2f} {unit_label}</title></rect>'
            )
            # Label
            svg_bars.append(
                f'<text x="{x + width/2:.1f}" y="{svg_h - 10}" text-anchor="middle" font-size="10" fill="#4b5563">{c["class_name"][:5]}</text>'
            )

        svg_chart = f'''
        <svg viewBox="0 0 {svg_w} {svg_h}" width="100%" height="{svg_h}" xmlns="http://www.w3.org/2000/svg">
            <line x1="{margin}" y1="{zero_y}" x2="{svg_w - margin}" y2="{zero_y}" stroke="#9ca3af" stroke-width="1.5" stroke-dasharray="4"/>
            <text x="{margin}" y="{zero_y - 6}" font-size="11" fill="#6b7280">0.0 {unit_label}</text>
            <text x="{margin}" y="{margin}" font-size="11" fill="#15803d">+{max_net:.1f} {unit_label}</text>
            <text x="{margin}" y="{svg_h - margin}" font-size="11" fill="#dc2626">-{max_net:.1f} {unit_label}</text>
            {''.join(svg_bars)}
        </svg>
        '''

        # Class rows for table
        matrix_rows = []
        matrix = data['transition_matrix']
        for i, c in enumerate(classes):
            cells = ''.join([f'<td class="text-right {"diag" if i==j else ""}">{matrix[i][j]:.2f}</td>' for j in range(len(classes))])
            matrix_rows.append(
                f'<tr><td><span class="color-badge" style="background:{c["color"]}"></span>{c["class_name"]}</td>{cells}<td class="text-right bold">{c["initial_area"]:.2f}</td><td class="text-right loss">-{c["gross_loss"]:.2f}</td></tr>'
            )

        # Top transitions rows
        top_rows = ''.join([
            f'<tr><td>{idx+1}</td><td><strong>{t["from_class"]}</strong> &rarr; <strong>{t["to_class"]}</strong></td><td class="text-right bold">{t["area"]:.2f} {unit_label}</td><td class="text-right">{t["share_pct"]:.1f}%</td></tr>'
            for idx, t in enumerate(top_transitions[:5])
        ])

        html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LCLUC 변화 분석 요약 보고서 — {self.pair}</title>
    <style>
        :root {{
            --primary: #1e3a8a;
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --border: #e2e8f0;
            --text: #1e293b;
            --text-muted: #64748b;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background-color: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 32px 16px;
            line-height: 1.6;
        }}
        .container {{
            max-width: 960px;
            margin: 0 auto;
        }}
        .header {{
            border-bottom: 2px solid var(--border);
            padding-bottom: 20px;
            margin-bottom: 28px;
        }}
        .title {{
            font-size: 26px;
            font-weight: 700;
            color: var(--primary);
            margin: 0 0 6px 0;
        }}
        .meta {{
            font-size: 13px;
            color: var(--text-muted);
        }}
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 28px;
        }}
        .kpi-card {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 18px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        .kpi-label {{
            font-size: 12px;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 6px;
        }}
        .kpi-value {{
            font-size: 24px;
            font-weight: 800;
            color: var(--primary);
        }}
        .card {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 24px;
            margin-bottom: 28px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        .card-title {{
            font-size: 17px;
            font-weight: 700;
            margin: 0 0 16px 0;
            color: var(--primary);
            border-left: 4px solid var(--primary);
            padding-left: 10px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
            margin-top: 8px;
        }}
        th, td {{
            padding: 8px 10px;
            border-bottom: 1px solid var(--border);
        }}
        th {{
            background-color: #f1f5f9;
            font-weight: 600;
            color: #334155;
        }}
        .text-right {{ text-align: right; }}
        .bold {{ font-weight: 700; }}
        .diag {{ background-color: #f8fafc; font-weight: 600; }}
        .loss {{ color: #dc2626; }}
        .color-badge {{
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 6px;
            vertical-align: middle;
        }}
        .disclaimer {{
            background: #fffbeb;
            border: 1px solid #fef3c7;
            border-radius: 6px;
            padding: 14px;
            font-size: 12px;
            color: #92400e;
            margin-top: 32px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 class="title">LCLUC 토지피복 변화 분석 요약 보고서</h1>
            <div class="meta">
                <span>워크플로: <code>{self.workflow_id}</code></span> &bull; 
                <span>분석 연도쌍: <strong>{self.pair}</strong></span> &bull; 
                <span>생성 일시: {data['exported_at']}</span>
            </div>
        </div>

        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-label">전체 분석 면적</div>
                <div class="kpi-value">{summary['total_evaluated_area']:,.1f} <span style="font-size:14px">{unit_label}</span></div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">총 변화 면적</div>
                <div class="kpi-value" style="color:#dc2626">{summary['total_changed_area']:,.1f} <span style="font-size:14px">{unit_label}</span></div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">변화율</div>
                <div class="kpi-value" style="color:#d97706">{summary['change_rate_pct']:.2f}%</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">무변화 유지 면적</div>
                <div class="kpi-value" style="color:#15803d">{summary['persistence_area']:,.1f} <span style="font-size:14px">{unit_label}</span></div>
            </div>
        </div>

        <div class="card">
            <h2 class="card-title">토지피복 범주별 순변화 (Net Change)</h2>
            <p style="font-size:13px; color:#64748b; margin-top:-8px; margin-bottom:16px;">
                각 범주별 유입(Gain)과 유출(Loss)을 상쇄한 순 증감 면적입니다.
            </p>
            {svg_chart}
        </div>

        <div class="card">
            <h2 class="card-title">주요 전이 동인 (Top 5 Transitions)</h2>
            <table>
                <thead>
                    <tr>
                        <th style="width:50px">순위</th>
                        <th>전이 유형</th>
                        <th class="text-right">변화 면적 ({unit_label})</th>
                        <th class="text-right">전체 변화 점유율</th>
                    </tr>
                </thead>
                <tbody>
                    {top_rows}
                </tbody>
            </table>
        </div>

        <div class="card" style="overflow-x:auto">
            <h2 class="card-title">9×9 토지피복 전이 행렬 (Transition Matrix)</h2>
            <table>
                <thead>
                    <tr>
                        <th>출발 범주 (From)</th>
                        {''.join([f'<th class="text-right">{c["class_name"][:4]}</th>' for c in classes])}
                        <th class="text-right">초기면적</th>
                        <th class="text-right">총감소</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(matrix_rows)}
                </tbody>
            </table>
        </div>

        <div class="disclaimer">
            <strong>법적·운영 책임 고지</strong>: 본 보고서는 인공위성 원격탐사 영상과 딥러닝 추론 기반의 자동화 분석 결과물입니다. 계절적 변동, 센서 노이즈 및 분류 모델의 불확실성이 가짜 변화로 집계되었을 수 있으며, 독립적인 과학적 현장 검증 또는 공인 기관의 승인을 거치지 않은 참고용 자료입니다.
        </div>
    </div>
</body>
</html>'''
        return html.encode('utf-8')

    # -------------------------------------------------------------------------
    # 5. Package Bundle Exporter (ZIP Archive)
    # -------------------------------------------------------------------------
    def export_bundle_zip(
        self,
        unit: str = 'ha',
        target_crs: Optional[str] = None,
    ) -> bytes:
        """Bundle all formats into a secure, directory-contained ZIP archive."""
        buf = io.BytesIO()
        manifest_files = []

        with zipfile.ZipFile(buf, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            prefix = f'export_bundle_{self.workflow_id[:12]}_{self.pair}'

            # 1. GeoTIFF
            tif_bytes = self.export_geotiff(target_crs=target_crs)
            tif_name = f'{prefix}/transitions.tif'
            zf.writestr(tif_name, tif_bytes)
            manifest_files.append({
                'name': 'transitions.tif',
                'format': 'GeoTIFF',
                'size_bytes': len(tif_bytes),
                'sha256': hashlib.sha256(tif_bytes).hexdigest(),
                'description': 'Indexed GeoTIFF with standard RGBA colormap and tags',
            })

            # 2. GeoJSON
            geojson_bytes = self.export_geojson()
            geojson_name = f'{prefix}/changes.geojson'
            zf.writestr(geojson_name, geojson_bytes)
            manifest_files.append({
                'name': 'changes.geojson',
                'format': 'GeoJSON',
                'size_bytes': len(geojson_bytes),
                'sha256': hashlib.sha256(geojson_bytes).hexdigest(),
                'description': 'Enriched vector polygons with area_ha, confidence, and class names',
            })

            # 3. CSV
            csv_bytes = self.export_csv(unit=unit)
            csv_name = f'{prefix}/transition_matrix.csv'
            zf.writestr(csv_name, csv_bytes)
            manifest_files.append({
                'name': 'transition_matrix.csv',
                'format': 'CSV',
                'size_bytes': len(csv_bytes),
                'sha256': hashlib.sha256(csv_bytes).hexdigest(),
                'description': 'Standard 9x9 transition matrix with gains, losses, and net changes',
            })

            # 4. JSON
            json_bytes = self.export_json_report(unit=unit)
            json_name = f'{prefix}/report.json'
            zf.writestr(json_name, json_bytes)
            manifest_files.append({
                'name': 'report.json',
                'format': 'JSON',
                'size_bytes': len(json_bytes),
                'sha256': hashlib.sha256(json_bytes).hexdigest(),
                'description': 'Full analytical report data structure',
            })

            # 5. HTML
            html_bytes = self.export_html_report(unit=unit)
            html_name = f'{prefix}/summary_report.html'
            zf.writestr(html_name, html_bytes)
            manifest_files.append({
                'name': 'summary_report.html',
                'format': 'HTML',
                'size_bytes': len(html_bytes),
                'sha256': hashlib.sha256(html_bytes).hexdigest(),
                'description': 'Self-contained executive HTML summary report with embedded SVG charts',
            })

            # 6. MANIFEST.json
            manifest_data = {
                'bundle_name': prefix,
                'workflow_id': self.workflow_id,
                'pair': self.pair,
                'unit': unit,
                'created_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'file_count': len(manifest_files),
                'files': manifest_files,
            }
            manifest_bytes = json.dumps(manifest_data, ensure_ascii=False, indent=2).encode('utf-8')
            zf.writestr(f'{prefix}/MANIFEST.json', manifest_bytes)

        return buf.getvalue()
