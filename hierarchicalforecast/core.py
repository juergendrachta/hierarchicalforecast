# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/core.ipynb (unless otherwise specified).

__all__ = ['HierarchicalReconciliation']

# Cell
from functools import partial
from inspect import signature
from typing import Callable, Dict, List, Optional

import numpy as np
import pandas as pd

# Internal Cell
def _build_fn_name(fn) -> str:
    fn_name = type(fn).__name__
    func_params = fn.__dict__
    func_params = [f'{name}-{value}' for name, value in func_params.items()]
    if func_params:
        fn_name += '_' + '_'.join(func_params)
    return fn_name

# Cell
class HierarchicalReconciliation:

    def __init__(
            self,
            reconcilers: List[Callable] # Reconciliation classes of the `methods` module
        ):
        self.reconcilers = reconcilers

    def reconcile(
            self,
            Y_h: pd.DataFrame, # Base forecasts with columns `ds` and models to reconcile indexed by `unique_id`.
            Y_df: pd.DataFrame, # Training set of base time series with columns `['ds', 'y']` indexed by `unique_id`
                                # If a class of `self.reconciles` receives
                                # `y_hat_insample`, `Y_df` must include them as columns.
            S: pd.DataFrame,    #  Summing matrix of size `(base, bottom)`.
            tags: Dict[str, np.ndarray] # Each key is a level and its value contains tags associated to that level.
        ):
        drop_cols = ['ds', 'y'] if 'y' in Y_h.columns else ['ds']
        model_names = Y_h.drop(columns=drop_cols, axis=1).columns.to_list()
        uids = Y_h.index.unique()
        # same order of Y_h to prevent errors
        S_ = S.loc[uids]
        common_vals = dict(
            y_insample = Y_df.pivot(columns='ds', values='y').loc[uids].values.astype(np.float32),
            S = S_.values.astype(np.float32),
            idx_bottom = S_.index.get_indexer(S.columns),
            levels={key: S_.index.get_indexer(val) for key, val in tags.items()}
        )
        fcsts = Y_h.copy()
        for reconcile_fn in self.reconcilers:
            reconcile_fn_name = _build_fn_name(reconcile_fn)
            has_fitted = 'y_hat_insample' in signature(reconcile_fn).parameters
            for model_name in model_names:
                # Remember: pivot sorts uid
                y_hat_model = Y_h.pivot(columns='ds', values=model_name).loc[uids].values
                if has_fitted:
                    if model_name in Y_df:
                        y_hat_insample = Y_df.pivot(columns='ds', values=model_name).loc[uids].values
                        y_hat_insample = y_hat_insample.astype(np.float32)
                        common_vals['y_hat_insample'] = y_hat_insample
                    else:
                        # some methods have the residuals argument
                        # but they don't need them
                        # ej MinTrace(method='ols')
                        common_vals['y_hat_insample'] = None
                kwargs = [key for key in signature(reconcile_fn).parameters if key in common_vals.keys()]
                kwargs = {key: common_vals[key] for key in kwargs}
                fcsts_model = reconcile_fn(y_hat=y_hat_model, **kwargs)
                fcsts[f'{model_name}/{reconcile_fn_name}'] = fcsts_model.flatten()
                if has_fitted:
                    del common_vals['y_hat_insample']
        return fcsts