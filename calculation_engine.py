from typing import Dict, List, Any

def compute_boe_costing(header: Dict[str, Any], items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    In-memory Python calculation matching the exact logic of the Calculation sheet.
    Returns computed header totals and enriched line item rows.
    """
    exchange_rate = float(header.get("exchange_rate") or 0.0)
    total_weight_kg = float(header.get("total_weight_kg") or 0.0)
    invoice_value_fc = float(header.get("invoice_value_fc") or 0.0)
    freight_inr = float(header.get("freight_inr") or 0.0)

    # Handle insurance rate (e.g. 1.125% -> 0.01125 or already decimal)
    raw_ins = float(header.get("insurance_percent") or 0.0)
    insurance_rate = raw_ins / 100.0 if raw_ins > 0.05 else raw_ins

    misc_fc = float(header.get("misc_charges") or 0.0)

    # Header calculations
    inv_value_inr = invoice_value_fc * exchange_rate
    misc_inr = misc_fc * exchange_rate
    insurance_inr = (inv_value_inr + misc_inr) * insurance_rate
    total_assessable_value = inv_value_inr + freight_inr + insurance_inr + misc_inr

    freight_per_kg = (freight_inr / total_weight_kg) if total_weight_kg > 0 else 0.0

    computed_items = []
    total_bcd = 0.0
    total_sws = 0.0
    total_igst = 0.0
    total_duty = 0.0

    for idx, item in enumerate(items, start=1):
        material_name = str(item.get("material_name") or f"Item {idx}")
        unit_price_fc = float(item.get("unit_price_fc") or 0.0)
        quantity = float(item.get("quantity") or 0.0)

        # BCD Rate: if passed as 7.5, convert to 0.075 for math, but keep percentage display
        raw_bcd = float(item.get("bcd_rate_percent") or 0.0)
        bcd_rate = raw_bcd / 100.0 if raw_bcd > 0.5 else raw_bcd
        bcd_rate_pct = bcd_rate * 100.0

        # Calculations per item
        item_inv_inr = unit_price_fc * quantity * exchange_rate
        item_freight_inr = (item_inv_inr / inv_value_inr * freight_inr) if inv_value_inr > 0 else 0.0
        item_misc_inr = (item_inv_inr / inv_value_inr * misc_inr) if inv_value_inr > 0 else 0.0
        item_ins_inr = (item_inv_inr + item_misc_inr) * insurance_rate
        item_assess_value = item_inv_inr + item_freight_inr + item_ins_inr + item_misc_inr

        item_bcd = item_assess_value * bcd_rate
        item_sws = item_bcd * 0.10
        item_igst = (item_assess_value + item_bcd + item_sws) * 0.18
        item_total_duty = item_bcd + item_sws + item_igst

        # Unit costs
        unit_cost_quoted_inr = unit_price_fc * exchange_rate
        unit_cost_actual_with_duty_gst = ((item_total_duty + item_assess_value) / quantity) if quantity > 0 else 0.0
        actual_cost_excl_gst = ((item_assess_value + item_bcd + item_sws) / quantity) if quantity > 0 else 0.0

        total_bcd += item_bcd
        total_sws += item_sws
        total_igst += item_igst
        total_duty += item_total_duty

        computed_items.append({
            "sr_no": idx,
            "material_name": material_name,
            "unit_price_fc": unit_price_fc,
            "quantity": quantity,
            "bcd_rate_pct": bcd_rate_pct,
            "bcd_rate_decimal": bcd_rate,
            "item_inv_inr": round(item_inv_inr, 2),
            "item_freight_inr": round(item_freight_inr, 2),
            "item_ins_inr": round(item_ins_inr, 2),
            "item_misc_inr": round(item_misc_inr, 2),
            "item_assess_value": round(item_assess_value, 2),
            "item_bcd": round(item_bcd, 2),
            "item_sws": round(item_sws, 2),
            "item_igst": round(item_igst, 2),
            "item_total_duty": round(item_total_duty, 2),
            "unit_cost_quoted_inr": round(unit_cost_quoted_inr, 2),
            "unit_cost_actual_with_duty_gst": round(unit_cost_actual_with_duty_gst, 2),
            "actual_cost_excl_gst": round(actual_cost_excl_gst, 2),
        })

    return {
        "header": {
            "total_weight_kg": total_weight_kg,
            "exchange_rate": exchange_rate,
            "invoice_value_fc": invoice_value_fc,
            "invoice_value_inr": round(inv_value_inr, 2),
            "freight_inr": freight_inr,
            "freight_per_kg": round(freight_per_kg, 2),
            "insurance_rate": insurance_rate,
            "insurance_percent_display": round(insurance_rate * 100, 3),
            "insurance_inr": round(insurance_inr, 2),
            "misc_charges_fc": misc_fc,
            "misc_charges_inr": round(misc_inr, 2),
            "total_assessable_value": round(total_assessable_value, 2),
            "total_bcd": round(total_bcd, 2),
            "total_sws": round(total_sws, 2),
            "total_igst": round(total_igst, 2),
            "total_duty": round(total_duty, 2),
        },
        "items": computed_items
    }
