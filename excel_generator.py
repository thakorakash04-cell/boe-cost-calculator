import os
import io
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from typing import Dict, List, Any

YELLOW_FILL = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
HEADER_FILL = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
WHITE_FONT = Font(name="Aptos Narrow", size=11, bold=True, color="FFFFFF")
THIN_BORDER = Border(
    left=Side(style='thin', color='A6A6A6'),
    right=Side(style='thin', color='A6A6A6'),
    top=Side(style='thin', color='A6A6A6'),
    bottom=Side(style='thin', color='A6A6A6')
)

def populate_boe_excel(
    header: Dict[str, Any],
    items: List[Dict[str, Any]],
    template_path: str = None,
    output_path: str = None
) -> bytes:
    """
    Populate the BOE Cost Calculation Form Excel template with extracted/edited values.
    Preserves all formulas, sheets, and formatting.
    """
    if template_path is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(base_dir, "templates", "BOE_Cost_Calculation_Form.xlsx")

    wb = openpyxl.load_workbook(template_path)

    # 1. Fill Input Form Sheet
    ws_input = wb["Input Form"]

    # Fill Header Inputs (Yellow Highlighted)
    ws_input["C5"] = float(header.get("total_weight_kg") or 0.0)
    ws_input["C6"] = float(header.get("exchange_rate") or 0.0)
    ws_input["C7"] = float(header.get("invoice_value_fc") or 0.0)
    ws_input["C8"] = float(header.get("freight_inr") or 0.0)

    # Insurance % (e.g. 0.01125 or 1.125%)
    ins_val = float(header.get("insurance_percent") or 0.0)
    if ins_val > 0.05:
        ins_val = ins_val / 100.0
    ws_input["C9"] = ins_val
    ws_input["C10"] = float(header.get("misc_charges") or 0.0)

    # Clear existing item rows or write new items
    start_row = 15
    for idx, item in enumerate(items):
        row = start_row + idx
        calc_row = 11 + idx

        ws_input[f"B{row}"] = item.get("material_name") or f"Material {idx+1}"
        ws_input[f"C{row}"] = float(item.get("unit_price_fc") or 0.0)
        ws_input[f"D{row}"] = float(item.get("quantity") or 0.0)

        # BCD Rate
        bcd_raw = float(item.get("bcd_rate_percent") or item.get("bcd_rate_pct") or 0.0)
        bcd_val = bcd_raw / 100.0 if bcd_raw > 0.5 else bcd_raw
        ws_input[f"E{row}"] = bcd_val

        # Formulas in Input Form
        ws_input[f"F{row}"] = f"=Calculation!O{calc_row}"
        ws_input[f"G{row}"] = f"=Calculation!P{calc_row}"
        ws_input[f"H{row}"] = f"=Calculation!Q{calc_row}"

        # Yellow fill on inputs
        for col_letter in ["B", "C", "D", "E"]:
            cell = ws_input[f"{col_letter}{row}"]
            cell.fill = YELLOW_FILL

    # 2. Update Calculation Sheet for extra items if needed
    ws_calc = wb["Calculation"]
    for idx, item in enumerate(items):
        calc_row = 11 + idx
        input_row = start_row + idx

        ws_calc[f"A{calc_row}"] = idx + 1
        ws_calc[f"B{calc_row}"] = f'=IF(\'Input Form\'!B{input_row}=""," ", \'Input Form\'!B{input_row})'
        ws_calc[f"C{calc_row}"] = f'=IF(\'Input Form\'!B{input_row}=""," ", \'Input Form\'!C{input_row})'
        ws_calc[f"D{calc_row}"] = f'=IF(\'Input Form\'!B{input_row}=""," ", \'Input Form\'!D{input_row})'
        ws_calc[f"E{calc_row}"] = f'=IF(\'Input Form\'!B{input_row}="","",C{calc_row}*D{calc_row}*$C$3)'
        ws_calc[f"F{calc_row}"] = f'=IF(\'Input Form\'!B{input_row}="","",IF($D$4=0,0,(E{calc_row}/$D$4)*$D$5))'
        ws_calc[f"G{calc_row}"] = f'=IF(\'Input Form\'!B{input_row}="","",(E{calc_row}+H{calc_row})*$C$6)'
        ws_calc[f"H{calc_row}"] = f'=IF(\'Input Form\'!B{input_row}="","",IF($D$4=0,0,(E{calc_row}/$D$4)*$D$7))'
        ws_calc[f"I{calc_row}"] = f'=IF(\'Input Form\'!B{input_row}="","",E{calc_row}+F{calc_row}+G{calc_row}+H{calc_row})'
        ws_calc[f"J{calc_row}"] = f'=IF(\'Input Form\'!B{input_row}=""," ",\'Input Form\'!E{input_row})'
        ws_calc[f"K{calc_row}"] = f'=IF(\'Input Form\'!B{input_row}="","",I{calc_row}*J{calc_row})'
        ws_calc[f"L{calc_row}"] = f'=IF(\'Input Form\'!B{input_row}="","",K{calc_row}*10%)'
        ws_calc[f"M{calc_row}"] = f'=IF(\'Input Form\'!B{input_row}="","",(I{calc_row}+K{calc_row}+L{calc_row})*18%)'
        ws_calc[f"N{calc_row}"] = f'=IF(\'Input Form\'!B{input_row}="","",K{calc_row}+L{calc_row}+M{calc_row})'
        ws_calc[f"O{calc_row}"] = f'=IF(\'Input Form\'!B{input_row}="","",C{calc_row}*$C$3)'
        ws_calc[f"P{calc_row}"] = f'=IF(\'Input Form\'!B{input_row}="","",IF(D{calc_row}=0,0,(N{calc_row}+I{calc_row})/D{calc_row}))'
        ws_calc[f"Q{calc_row}"] = f'=IF(\'Input Form\'!B{input_row}="","",IF(D{calc_row}=0,0,(I{calc_row}+K{calc_row}+L{calc_row})/D{calc_row}))'

    if output_path:
        wb.save(output_path)
        with open(output_path, "rb") as f:
            return f.read()
    else:
        stream = io.BytesIO()
        wb.save(stream)
        return stream.getvalue()
