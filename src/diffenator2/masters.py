import collections
import io
import itertools
import logging
import os
import sys

from fontTools import ttLib
from fontTools.varLib.models import piecewiseLinearMap
from fontTools.varLib import instancer


_TABLES_WITH_ITEM_VARIATIONS = ['MVAR', 'VVAR', 'HVAR', 'GDEF']

_TABLES_WITH_VARIATIONS = ['MVAR', 'VVAR', 'HVAR', 'GDEF', 'gvar', 'cvar']

logging.getLogger('fontTools').setLevel(logging.WARNING)


def find_masters(ttfont):
    results = []
    axis_peaks = _FindPeaks(ttfont)

    # add min and max for each axis as well
    for axis in ttfont["fvar"].axes:
      if not axis.axisTag in axis_peaks:
        axis_peaks[axis.axisTag] = set()
      axis_peaks[axis.axisTag].add(axis.minValue)
      axis_peaks[axis.axisTag].add(axis.maxValue)
    
    # generate combinations from peaks
    for combo in itertools.product(*axis_peaks.values()):
        results.append(dict(zip(axis_peaks.keys(), combo)))
    return results


def _FindPeaks(ttf):
  """Returns peaks for each axis"""
  result = {}

  # Collect peak values from all variation tables.
  varstore_fn = _GetVarStoreFunction(ttf['fvar'].axes)
  for table_name in _TABLES_WITH_VARIATIONS:
    if table_name in ttf:
      result.update(
          _AddPeaksFromVariationStore(ttf[table_name], varstore_fn, table_name))

  # Drop axes which don't have more than one peak.
  result = {k: v for k, v in result.items() if len(v) > 1}

  # Apply reverse avar mapping to the peak values of all axes.
  if 'avar' in ttf:
    result = _ReverseAvarMapping(ttf['avar'], result)

  # Include the default position(0) in the list of peak values.
  for v in result.values():
    v.add(0)

  axes = {
      a.axisTag: {
          -1: a.minValue, 0: a.defaultValue, 1: a.maxValue
      } for a in ttf['fvar'].axes
  }

  # Convert normalized values to user scale values (Ex: 0.0 -> 400).
  return {
      k: {round(piecewiseLinearMap(a, axes[k]), 2) for a in v
         } for k, v in result.items()
  }


def _ReverseAvarMapping(avar, axis_values):
  """Returns reverse avar mapping value.

  Takes input axis value and reverses avar processing to return the original
  normalized axis value. If avar in font has a mapping from X -> Y then passing
  Y to this function will return X.

  Returns:
    Reverse avar mapped value.

  Args:
    avar: avar table in font.
    axis_values: map containing a list of values for each axis.
  """

  # Collect avar segments and creates a new mapping by reversing it.
  maps = avar.segments
  reverse_avar_mapping = {
      k: {i[1]: i[0] for i in maps[k].items()} for k in maps.keys()
  }

  # Apply new reversed avar mapping. piecewiseLinearMap helps in mapping values
  # which lie in between segments by using a linear function.
  return {
      k: {piecewiseLinearMap(a, reverse_avar_mapping[k]) for a in v
         } for k, v in axis_values.items()
  }


def _AddPeaksFromVariationStore(table, varstore_fn, table_name):
  """Adds axes peaks from Variation Stores: both Tuple and Item."""

  result = collections.defaultdict(set)

  for tuple_store in varstore_fn[table_name](table):
    for var in tuple_store:
      for key, value in var.axes.items():
        result[key].add(value[1])

  return result


def _GetVarStoreFunction(fvar_axes):
  """Constructs a mapping from table name to lambdas which return var data."""

  varstore_fn = {
      'gvar': lambda t: t.variations.values(),
      'cvar': lambda t: [t.variations]
  }
  # Add lambdas for Item Var Stores.
  item_store_lambda = lambda t: _ConvertItemStore(t.table.VarStore, fvar_axes)
  varstore_fn.update(
      dict.fromkeys(_TABLES_WITH_ITEM_VARIATIONS, item_store_lambda))
  return varstore_fn


def _ConvertItemStore(item_store, fvar_axes):
  """Converts an Item Variation Store to a Tuple Store representation."""

  return instancer._TupleVarStoreAdapter.fromItemVarStore(
      item_store,
      fvar_axes,
  ).tupleVarData
