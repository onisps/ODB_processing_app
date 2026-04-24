# -*- coding: utf-8 -*-
from __future__ import print_function

import csv
import datetime
import json
import os
import sys
import traceback

from abaqusConstants import *
from odbAccess import openOdb


def report_progress(current, total, message):
    print("PROGRESS:%d:%d:%s" % (current, total, message))
    sys.stdout.flush()


def safe_mkdir(path):
    if not os.path.exists(path):
        os.makedirs(path)


def sanitize(name):
    forbidden = r'\/:*?"<>|'
    for ch in forbidden:
        name = name.replace(ch, "_")
    return name


def save_to_csv(filepath, time_array, data_array, headers):
    with open(filepath, "wb") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(headers)
        for i in range(len(time_array)):
            t = time_array[i]
            d = data_array[i]
            if isinstance(d, list) or isinstance(d, tuple):
                row = ["%.6f" % t] + ["%.6f" % val for val in d]
            else:
                row = ["%.6f" % t, "%.6f" % d]
            writer.writerow(row)


def _to_text(x):
    try:
        if isinstance(x, unicode):
            return x.encode("utf-8")
    except Exception:
        pass
    try:
        return str(x)
    except Exception:
        return repr(x)


def scan_odb(odb_path):
    odb = openOdb(path=odb_path, readOnly=True)
    try:
        inst_map = {}
        for inst_name, instance in odb.rootAssembly.instances.items():
            inst_fields = {}
            for step in odb.steps.values():
                for frame in step.frames:
                    for field_name, fo in frame.fieldOutputs.items():
                        info = inst_fields.get(field_name)
                        if info is None:
                            info = {"components": [], "invariants": []}
                            inst_fields[field_name] = info

                        try:
                            comps = list(fo.componentLabels) if fo.componentLabels else []
                        except Exception:
                            comps = []
                        for c in comps:
                            c_txt = _to_text(c)
                            if c_txt not in info["components"]:
                                info["components"].append(c_txt)

                        try:
                            invs = list(fo.validInvariants) if fo.validInvariants else []
                        except Exception:
                            invs = []
                        for inv in invs:
                            inv_txt = _to_text(inv)
                            if inv_txt not in info["invariants"]:
                                info["invariants"].append(inv_txt)

            elsets = []
            try:
                elsets = list(instance.elementSets.keys())
            except Exception:
                elsets = []
            nsets = []
            try:
                nsets = list(instance.nodeSets.keys())
            except Exception:
                nsets = []

            bodies = {}
            bodies["ALL"] = {"label": "ALL", "type": "instance", "name": inst_name, "Fields": inst_fields}
            for s in elsets:
                key = "ELSET:" + _to_text(s)
                bodies[key] = {"label": "ELSET " + _to_text(s), "type": "elementSet", "name": _to_text(s), "Fields": inst_fields}
            for s in nsets:
                key = "NSET:" + _to_text(s)
                bodies[key] = {"label": "NSET " + _to_text(s), "type": "nodeSet", "name": _to_text(s), "Fields": inst_fields}

            inst_map[_to_text(inst_name)] = {"Bodies": bodies}

        history = {}
        for step in odb.steps.values():
            for region_name, region in step.historyRegions.items():
                region_txt = _to_text(region_name)
                vars_list = history.get(region_txt)
                if vars_list is None:
                    vars_list = []
                    history[region_txt] = vars_list
                try:
                    keys = list(region.historyOutputs.keys())
                except Exception:
                    keys = []
                for k in keys:
                    k_txt = _to_text(k)
                    if k_txt not in vars_list:
                        vars_list.append(k_txt)

        return {"command": "scan", "Instances": inst_map, "HistoryOutputs": history, "odb_path": _to_text(odb_path)}
    finally:
        odb.close()


def _resolve_region(instance, body_key):
    if body_key == "ALL":
        return instance
    if body_key.startswith("ELSET:"):
        name = body_key.split(":", 1)[1]
        return instance.elementSets[name]
    if body_key.startswith("NSET:"):
        name = body_key.split(":", 1)[1]
        return instance.nodeSets[name]
    return instance


def _scalarize_field(field_output, variant_type, variant):
    if variant_type == "scalar":
        return field_output, "Value"
    if variant_type == "component":
        return field_output.getSubset(componentLabel=variant), variant
    if variant_type == "invariant":
        inv_const = globals().get(variant)
        if inv_const is None:
            inv_const = globals().get(_to_text(variant))
        return field_output.getScalarField(invariant=inv_const), variant
    return field_output, _to_text(variant)


def extract_odb(odb_path, export_root, selection):
    odb = openOdb(path=odb_path, readOnly=True)
    try:
        odb_basename = os.path.splitext(os.path.basename(odb_path))[0]
        date_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        root_dir = os.path.join(export_root, "%s_%s" % (sanitize(odb_basename), date_str))
        safe_mkdir(root_dir)

        if selection is None:
            scan = scan_odb(odb_path)
            fields = []
            for inst_name, inst_info in scan.get("Instances", {}).items():
                body_key = "ALL"
                body_info = inst_info.get("Bodies", {}).get(body_key, {})
                for field_name, field_info in (body_info.get("Fields") or {}).items():
                    comps = field_info.get("components") or []
                    invs = field_info.get("invariants") or []
                    if comps:
                        for c in comps:
                            fields.append(
                                {
                                    "kind": "field",
                                    "instance": inst_name,
                                    "body_key": body_key,
                                    "field": field_name,
                                    "variant_type": "component",
                                    "variant": c,
                                }
                            )
                    elif invs:
                        for inv in invs:
                            fields.append(
                                {
                                    "kind": "field",
                                    "instance": inst_name,
                                    "body_key": body_key,
                                    "field": field_name,
                                    "variant_type": "invariant",
                                    "variant": inv,
                                }
                            )
                    else:
                        fields.append(
                            {
                                "kind": "field",
                                "instance": inst_name,
                                "body_key": body_key,
                                "field": field_name,
                                "variant_type": "scalar",
                                "variant": "Value",
                            }
                        )

            history = []
            for region, vars_list in (scan.get("HistoryOutputs") or {}).items():
                for var in vars_list:
                    history.append({"kind": "history", "region": region, "variable": var})

            selection = {"fields": fields, "history": history, "aggregations": ["Mean", "Max", "Min", "Boxplot stats"]}

        selected_fields = selection.get("fields") or []
        selected_history = selection.get("history") or []
        aggregations = selection.get("aggregations") or []

        total_tasks = max(1, len(selected_fields) * max(1, len(aggregations)) + len(selected_history))
        report_progress(0, total_tasks, "Starting extraction...")
        current_task = 0

        out_structure = {"command": "extract", "csv_root": os.path.abspath(root_dir), "Instances": {}, "HistoryOutputs": {}}

        for item in selected_fields:
            inst_name = item.get("instance")
            body_key = item.get("body_key", "ALL")
            field_name = item.get("field")
            variant_type = item.get("variant_type")
            variant = item.get("variant")

            if inst_name not in odb.rootAssembly.instances:
                continue
            instance = odb.rootAssembly.instances[inst_name]
            try:
                region = _resolve_region(instance, body_key)
            except Exception:
                region = instance

            inst_out = out_structure["Instances"].get(inst_name)
            if inst_out is None:
                inst_out = {"Bodies": {}}
                out_structure["Instances"][inst_name] = inst_out

            body_out = inst_out["Bodies"].get(body_key)
            if body_out is None:
                body_out = {"Fields": {}}
                inst_out["Bodies"][body_key] = body_out

            field_out = body_out["Fields"].get(field_name)
            if field_out is None:
                field_out = {"Variants": {}}
                body_out["Fields"][field_name] = field_out

            variant_label = _to_text(variant)
            variant_out = field_out["Variants"].get(variant_label)
            if variant_out is None:
                variant_out = {"Aggregations": []}
                field_out["Variants"][variant_label] = variant_out

            inst_dir = os.path.join(root_dir, sanitize(inst_name))
            safe_mkdir(inst_dir)
            body_dir = os.path.join(inst_dir, sanitize(body_key))
            safe_mkdir(body_dir)
            field_dir = os.path.join(body_dir, sanitize(field_name))
            safe_mkdir(field_dir)
            var_dir = os.path.join(field_dir, sanitize(variant_label))
            safe_mkdir(var_dir)

            time_vals = []
            header_name = variant_label
            values_by_agg = {}
            for agg in aggregations:
                values_by_agg[agg] = []

            for step in odb.steps.values():
                for frame in step.frames:
                    if field_name not in frame.fieldOutputs:
                        continue
                    time_vals.append(frame.frameValue)
                    fo = frame.fieldOutputs[field_name]
                    try:
                        if field_name in ["S", "LE", "PE", "EE"]:
                            try:
                                fo = fo.getSubset(position=INTEGRATION_POINT, region=region)
                            except Exception:
                                fo = fo.getSubset(region=region)
                        else:
                            fo = fo.getSubset(region=region)

                        scalar_fo, header_name = _scalarize_field(fo, variant_type, variant_label)
                        vals = []
                        for v in scalar_fo.values:
                            try:
                                vals.append(float(v.data))
                            except Exception:
                                pass

                        if vals:
                            s = sorted(vals)
                            n = len(s)
                            mean_v = sum(vals) / float(len(vals))
                            min_v = s[0]
                            max_v = s[-1]
                            q1 = s[int(n * 0.25)]
                            med = s[int(n * 0.5)]
                            q3 = s[int(n * 0.75)]
                            if "Mean" in values_by_agg:
                                values_by_agg["Mean"].append(mean_v)
                            if "Max" in values_by_agg:
                                values_by_agg["Max"].append(max_v)
                            if "Min" in values_by_agg:
                                values_by_agg["Min"].append(min_v)
                            if "Boxplot stats" in values_by_agg:
                                values_by_agg["Boxplot stats"].append([min_v, q1, med, q3, max_v])
                        else:
                            if "Mean" in values_by_agg:
                                values_by_agg["Mean"].append(0.0)
                            if "Max" in values_by_agg:
                                values_by_agg["Max"].append(0.0)
                            if "Min" in values_by_agg:
                                values_by_agg["Min"].append(0.0)
                            if "Boxplot stats" in values_by_agg:
                                values_by_agg["Boxplot stats"].append([0.0] * 5)
                    except Exception:
                        if "Mean" in values_by_agg:
                            values_by_agg["Mean"].append(0.0)
                        if "Max" in values_by_agg:
                            values_by_agg["Max"].append(0.0)
                        if "Min" in values_by_agg:
                            values_by_agg["Min"].append(0.0)
                        if "Boxplot stats" in values_by_agg:
                            values_by_agg["Boxplot stats"].append([0.0] * 5)

            for agg in aggregations:
                current_task += 1
                report_progress(current_task, total_tasks, "Saving %s %s %s" % (inst_name, field_name, agg))
                if agg == "Boxplot stats":
                    save_to_csv(
                        os.path.join(var_dir, "%s.csv" % sanitize(agg)),
                        time_vals,
                        values_by_agg.get(agg, []),
                        ["Time", "Min", "Q1", "Median", "Q3", "Max"],
                    )
                else:
                    save_to_csv(
                        os.path.join(var_dir, "%s.csv" % sanitize(agg)),
                        time_vals,
                        values_by_agg.get(agg, []),
                        ["Time", header_name],
                    )
                if agg not in variant_out["Aggregations"]:
                    variant_out["Aggregations"].append(agg)

        history_root = os.path.join(root_dir, "history")
        safe_mkdir(history_root)
        for item in selected_history:
            region = item.get("region")
            variable = item.get("variable")
            current_task += 1
            report_progress(current_task, total_tasks, "Extracting history %s" % _to_text(variable))

            all_time = []
            all_data = []
            for step in odb.steps.values():
                if region in step.historyRegions:
                    region_obj = step.historyRegions[region]
                    if variable in region_obj.historyOutputs:
                        ho = region_obj.historyOutputs[variable]
                        for t, v in ho.data:
                            all_time.append(t)
                            all_data.append(v)

            if all_time:
                region_dir = os.path.join(history_root, sanitize(region))
                safe_mkdir(region_dir)
                var_dir = os.path.join(region_dir, sanitize(variable))
                safe_mkdir(var_dir)
                save_to_csv(os.path.join(var_dir, "History.csv"), all_time, all_data, ["Time", _to_text(variable)])
                region_out = out_structure["HistoryOutputs"].get(region)
                if region_out is None:
                    region_out = {}
                    out_structure["HistoryOutputs"][region] = region_out
                region_out[_to_text(variable)] = True

        with open("abaqus_output.json", "wb") as f:
            json.dump(out_structure, f)

        report_progress(total_tasks, total_tasks, "Extraction complete.")
        return out_structure
    finally:
        odb.close()


def main():
    print("EXTRACTOR_STARTED")

    input_file = None
    for arg in sys.argv:
        if arg.endswith(".json"):
            input_file = os.path.abspath(arg)
            break

    if not input_file:
        if len(sys.argv) >= 2 and sys.argv[1].endswith(".odb"):
            extract_odb(sys.argv[1], "extracted_data", None)
            return
        print("ERROR: No input configuration found.")
        sys.exit(1)

    with open(input_file, "r") as f:
        args = json.load(f)

    def byteify(input):
        if isinstance(input, dict):
            return {byteify(key): byteify(value) for key, value in input.iteritems()}
        elif isinstance(input, list):
            return [byteify(element) for element in input]
        elif isinstance(input, unicode):
            enc = sys.getfilesystemencoding() or "mbcs"
            try:
                return input.encode(enc)
            except Exception:
                try:
                    return input.encode("mbcs")
                except Exception:
                    return input.encode("utf-8")
        else:
            return input

    args = byteify(args)

    odb_path = args["odb_path"]
    command = args.get("command")
    params = args.get("params", {}) or {}
    selection = args.get("selection")

    try:
        if command == "scan":
            result = scan_odb(odb_path)
            with open("abaqus_output.json", "wb") as f:
                json.dump(result, f)
        else:
            export_root = params.get("export_root", "extracted_data")
            extract_odb(odb_path, export_root, selection)
    except Exception:
        with open("abaqus_error.log", "wb") as f:
            f.write(traceback.format_exc())
        print("ERROR:Extraction failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
