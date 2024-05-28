from __future__ import annotations

import json
from copy import deepcopy as copy

from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._c_m_a_p import table__c_m_a_p
from fontTools.ttLib.tables._f_v_a_r import table__f_v_a_r
from fontTools.ttLib.tables._g_l_y_f import (
    ARG_1_AND_2_ARE_WORDS,
    ARGS_ARE_XY_VALUES,
    MORE_COMPONENTS,
    NON_OVERLAPPING,
    OVERLAP_COMPOUND,
    ROUND_XY_TO_GRID,
    SCALED_COMPONENT_OFFSET,
    UNSCALED_COMPONENT_OFFSET,
    USE_MY_METRICS,
    WE_HAVE_A_SCALE,
    WE_HAVE_A_TWO_BY_TWO,
    WE_HAVE_AN_X_AND_Y_SCALE,
    WE_HAVE_INSTRUCTIONS,
    Glyph,
    flagCubic,
    flagOnCurve,
    flagOverlapSimple,
)
from fontTools.ttLib.tables._k_e_r_n import table__k_e_r_n
from fontTools.ttLib.tables._n_a_m_e import table__n_a_m_e
from fontTools.ttLib.tables.S_T_A_T_ import table_S_T_A_T_

class_defs = {
    1: "Base Glyph",
    2: "Ligature Glyph",
    3: "Mark Glyph",
    4: "Component Glyph",
}


def serialise_name_table(obj):
    return {
        f"{r.nameID}/{r.platformID}/{r.platEncID}/{r.langID}": r.toUnicode()
        for r in obj.names
    }


def serialise_fvar_table(obj, root):
    nametbl = root["name"]
    axes = {
        a.axisTag: {
            "minValue": a.minValue,
            "maxValue": a.maxValue,
            "defaultValue": a.defaultValue,
            "axisName": nametbl.getName(a.axisNameID, 3, 1, 0x409).toUnicode(),
            # TODO get axis Name Value (will need ttFont obj)
        }
        for a in obj.axes
    }

    instances = {
        nametbl.getName(i.subfamilyNameID, 3, 1, 0x409).toUnicode(): {
            "coordinates": i.coordinates,
            "postscriptName": (
                None
                if i.postscriptNameID in (None, 0xFFFF)
                else nametbl.getName(i.postscriptNameID, 3, 1, 0x409).toUnicode()
            ),
            "flags": i.flags,
        }
        for i in obj.instances
    }
    return {"axes": axes, "instances": instances}


def serialise_stat_table(obj, root):
    nametbl = root["name"]
    design_records = {
        d.AxisTag: {
            "order": d.AxisOrdering,
            "AxisName": nametbl.getName(d.AxisNameID, 3, 1, 0x409).toUnicode(),
        }
        for d in obj.table.DesignAxisRecord.Axis
    }
    if not obj.table.AxisValueArray:
        return {"design axis records": design_records}
    try:
        axis_values = {
            nametbl.getName(a.ValueNameID, 3, 1, 0x409).toUnicode(): {
                "format": a.Format,
                "AxisIndex": a.AxisIndex,
                "Flags": a.Flags,
                "Value": a.Value,
            }
            for a in obj.table.AxisValueArray.AxisValue
        }
    except:
        return {}
    return {"axis values": axis_values, "design axis records": design_records}


def serialise_cmap(obj):
    return {f"0x{hex(k)[2:].zfill(4).upper()}": v for k, v in obj.getBestCmap().items()}


def serialise_kern(obj):
    return [
        {"/".join(k): v for k, v in table.kernTable.items()} for table in obj.kernTables
    ]


def bit_list(bits, cast_list):
    res = []
    for bit, name in cast_list:
        if bits & bit == bit:
            res.append((hex(bit), name))
    return res


def serialise_component(compo):
    from fontTools.misc.fixedTools import fixedToFloat as fi2fl
    from fontTools.misc.fixedTools import floatToFixed as fl2fi
    from fontTools.misc.fixedTools import floatToFixedToStr as fl2str
    from fontTools.misc.fixedTools import strToFixedToFloat as str2fl

    attrs = {"glyphName": compo.glyphName}
    if not hasattr(compo, "firstPt"):
        attrs["x"] = compo.x
        attrs["y"] = compo.y
    else:
        attrs["firstPt"] = compo.firstPt
        attrs["secondPt"] = compo.secondPt

    if hasattr(compo, "transform"):
        transform = compo.transform
        if transform[0][1] or transform[1][0]:
            attrs["scalex"] = fl2str(transform[0][0], 14)
            attrs["scale01"] = fl2str(transform[0][1], 14)
            attrs["scale10"] = fl2str(transform[1][0], 14)
            attrs["scaley"] = fl2str(transform[1][1], 14)
        elif transform[0][0] != transform[1][1]:
            attrs["scalex"] = fl2str(transform[0][0], 14)
            attrs["scaley"] = fl2str(transform[1][1], 14)
        else:
            attrs["scale"] = fl2str(transform[0][0], 14)
    compo_bit_list = [
        (ARG_1_AND_2_ARE_WORDS, "ARG_1_AND_2_ARE_WORDS"),
        (ARGS_ARE_XY_VALUES, "ARGS_ARE_XY_VALUES"),
        (ROUND_XY_TO_GRID, "ROUND_XY_TO_GRID"),
        (WE_HAVE_A_SCALE, "WE_HAVE_A_SCALE"),
        (MORE_COMPONENTS, "MORE_COMPONENTS"),
        (WE_HAVE_AN_X_AND_Y_SCALE, "WE_HAVE_AN_X_AND_Y_SCALE"),
        (WE_HAVE_A_TWO_BY_TWO, "WE_HAVE_A_TWO_BY_TWO"),
        (WE_HAVE_INSTRUCTIONS, "WE_HAVE_INSTRUCTIONS"),
        (USE_MY_METRICS, "USE_MY_METRICS"),
        (OVERLAP_COMPOUND, "OVERLAP_COMPOUND"),
        (SCALED_COMPONENT_OFFSET, "SCALED_COMPONENT_OFFSET"),
        (UNSCALED_COMPONENT_OFFSET, "UNSCALED_COMPONENT_OFFSET"),
    ]
    attrs["flags"] = bit_list(compo.flags, compo_bit_list)
    return attrs


def serialise_glyph(obj, root):
    if obj.isComposite():
        return {
            f"Component {i}: {c.glyphName}": serialise_component(c)
            for i, c in enumerate(obj.components)
        }
    else:
        last = 0
        contours = {}
        for i in range(obj.numberOfContours):
            path_key = f"Contour: {i}"
            if i not in contours:
                contours[path_key] = {}
            contour = {}
            for j in range(last, obj.endPtsOfContours[i] + 1):
                node_key = f"Node: {j}"
                attrs = {
                    "x": obj.coordinates[j][0],
                    "y": obj.coordinates[j][1],
                    "on": obj.flags[j] & flagOnCurve,
                }
                if obj.flags[j] & flagOverlapSimple:
                    # Apple's rasterizer uses flagOverlapSimple in the first contour/first pt to flag glyphs that contain overlapping contours
                    attrs["overlap bit"] = True
                if obj.flags[j] & flagCubic:
                    attrs["cubic"] = True
                contour[node_key] = attrs
            last = obj.endPtsOfContours[i] + 1
            contours[path_key] = contour
        return contours


def TTJ(ttFont):
    # we must compile the glyph in order to access coordinates etc
    ttFont["glyf"].compile(ttFont)
    root = ttFont
    return _TTJ(ttFont, root)


def _TTJ(obj, root=None, depth=1):
    """Convert a TTFont to Basic python types"""
    if isinstance(obj, (float, int, str, bool)):
        return obj
    # custom
    elif isinstance(obj, table__n_a_m_e):
        return serialise_name_table(obj)

    elif isinstance(obj, table__f_v_a_r):
        return serialise_fvar_table(obj, root)

    elif isinstance(obj, table_S_T_A_T_):
        return serialise_stat_table(obj, root)

    elif isinstance(obj, table__c_m_a_p):
        return serialise_cmap(obj)

    elif isinstance(obj, table__k_e_r_n):
        return serialise_kern(obj)

    elif isinstance(obj, Glyph):
        return serialise_glyph(obj, root)

    elif isinstance(obj, TTFont):
        if depth > 1:
            return None
        return {
            k: _TTJ(obj[k], root)
            for k in obj.keys()
            if k not in ["loca", "GPOS", "GSUB", "GVAR"]
        }
    elif isinstance(obj, dict):
        return {k: _TTJ(v, root) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple, set)):
        return [_TTJ(i, root) for i in obj]
    elif hasattr(obj, "__dict__"):
        return {k: _TTJ(getattr(obj, k), root, depth=depth + 1) for k in vars(obj)}
    return obj


class Diff:
    def __init__(self, obj_a, obj_b):
        """A basic general purposes dict differ. Should not be tied to fonts!"""
        self.obj_a = obj_a
        self.obj_b = obj_b
        self.diff = self.clean(self._diff(self.obj_a, self.obj_b))

    def _diff(self, obj1, obj2, path=[]):
        """Diff to json objects. Output as html"""
        if obj1 is None and obj2 is None:
            return False
        elif isinstance(obj1, (int, float, str)) and isinstance(
            obj2, (int, float, str)
        ):
            if obj1 == obj2:
                return False
            return obj1, obj2
        elif isinstance(obj1, (int, float, str)) and obj2 is None:
            return obj1, obj2
        elif obj1 is None and isinstance(obj2, (int, float, str)):
            return obj1, obj2

        res = {}
        if isinstance(obj1, dict) and isinstance(obj2, dict):
            for k in set(obj1.keys()) | set(obj2.keys()):
                if k in obj1 and k in obj2:
                    res[k] = self._diff(obj1[k], obj2[k], path + [k])
                elif k in obj1 and k not in obj2:
                    res[k] = self._diff(obj1[k], None, path + [k])
                else:
                    res[k] = self._diff(None, obj2[k], path + [k])
        elif isinstance(obj1, dict) and not isinstance(obj2, dict):
            for k in obj1:
                res[k] = self._diff(obj1[k], obj2, path=path + [k])
        elif not isinstance(obj1, dict) and isinstance(obj2, dict):
            for k in obj2:
                res[k] = self._diff(obj1, obj2[k], path + [k])
        if isinstance(obj1, list) and isinstance(obj2, list):
            for i in range(max(len(obj1), len(obj2))):
                if i < len(obj1) and i < len(obj2):
                    res[i] = self._diff(obj1[i], obj2[i], path + [i])
                elif i < len(obj1) and i >= len(obj2):
                    res[i] = self._diff(obj1[i], None, path + [i])
                else:
                    res[i] = self._diff(None, obj2[i], path + [i])
        elif isinstance(obj1, list) and not isinstance(obj2, list):
            for i in range(len(obj1)):
                res[i] = self._diff(obj1[i], obj2, path + [i])
        elif not isinstance(obj1, list) and isinstance(obj2, list):
            for i in range(len(obj2)):
                res[i] = self._diff(obj1, obj2[i], path + [i])
        return res

    def clean(self, obj):
        """Remove any paths which are False or contain too many changes"""
        if obj is None:
            return None
        if isinstance(obj, tuple):
            return list(obj)
        if obj == False:
            return False
        res = copy(obj)
        for k, v in obj.items():
            res[k] = self.clean(v)
            if res[k] == False or not res[k]:
                res.pop(k)
        if len(res) >= 200:
            return {"error": (f"There are {len(res)} changes, check manually!", "")}
        return res

    def render(self):
        return f"<script>var fontdiff = {json.dumps(self.diff)};</script>"

    def summary(self):
        raise NotImplementedError()


# class TTJDiff(Diff):
#     def summary(self):
#         doc = []
#         obj = self.diff
#         try:
#             font_revision = obj["head"]["fontRevision"]
#             if font_revision[0] == font_revision[1]:
#                 doc.append(f"<li>head.fontRevision is same {font_revision[0]}</li>")
#             elif font_revision[0] > font_revision[1]:
#                 doc.append(
#                     f"<li>head.fontRevision is less than older version {font_revision[0]} {font_revision[1]}</li>"
#                 )
#             else:
#                 doc.append(
#                     f"<li>head.fontRevision has been incremented from {font_revision[0]} to {font_revision[1]}</li>"
#                 )
#         except:
#             pass

#         try:
#             avar = obj["avar"]["segments"]
#             if avar:
#                 doc.append(
#                     "<li>Avar table has been modified. Please check all diffs to see if glyph color is lighter/darker.</li>"
#                 )
#         except:
#             pass

#         try:
#             names = obj["name"]
#             nameids = set(k[0] for k, v in names.items() if v)
#             menu_nameids = set([1, 2, 4, 6, 16, 17, 21, 22])

#             changed_menu_nameids = menu_nameids & nameids
#             if changed_menu_nameids:
#                 doc.append(
#                     f"<li>NameIDs {changed_menu_nameids} have changed. This may affect application font menus.</li>"
#                 )

#             changed_ps_nameid = set([6]) & nameids
#             if changed_ps_nameid:
#                 doc.append(
#                     f"<li>Postscript name has changed. This may cause issues for Adobe users if they update their fonts.</li>"
#                 )

#             changed_vf_ps_name = set([25]) & nameids
#             if changed_vf_ps_name:
#                 doc.append(
#                     f"<li>nameID {25} has changed (Variations PostScript Name Prefix)</li>"
#                 )
#         except:
#             pass

#         # FIX THIS
#         try:
#             for k, v in obj.items():
#                 if all(vv[0] == None for _, vv in v.items()):
#                     doc.append(f"<li>{k} table has been added</li>")
#                 elif all(vv[1] == None for _, vv in v.items()):
#                     doc.append(f"<li>{k} table has been removed</li>")
#         except:
#             pass
#         return "\n".join(doc)
