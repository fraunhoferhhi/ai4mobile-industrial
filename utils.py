import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from datetime import datetime


def utc2berlin(datetime_index):
    """
    @param datetime_index: A non-localized datetime index of type `datetime64[ns]` or similar
    @return: a CEST localized datetime index of type `datetime64[ns, Europe/Berlin]`
    """
    return datetime_index.tz_localize("UTC").tz_convert("Europe/Berlin")


def add_timestamp_index(df_xy, epoch_label, index_label="timestamp", localize=True):
    """

    Add a timestamp index as `datetime64[ns, Europe/Berlin]` (default) or `datetime64[ns]` (`localized=False`)
    to a pandas.DataFrame with epoch timestamps

    @param df_xy: Input DataFrame
    @param epoch_label: type str, name of the label that contains the epoch timestamps
    @param index_label: type str, name of the added index. Defaults to "timestamp"
    @param localize: type bool, indicate whether to localize the timestamps. Defaults to True
    @return: pandas.DataFrame with a datetime index
    """
    df_ts = df_xy.assign(**{index_label: df_xy[epoch_label].apply(datetime.utcfromtimestamp)})
    df_ts = df_ts.set_index(index_label)
    if localize:
        df_ts.index = utc2berlin(df_ts.index)
    return df_ts.sort_index()   # DataFrame.sort_index() is always a good idea!!


def write_meta(df_xy, filename, index=None):
    nancount = df_xy.isna().sum()
    nanperc = 100-((nancount/len(df_xy))*100)  # percent of available data
    zerocount = (df_xy == 0).sum(axis=0)  # how many zeros per col
    nanmeta = pd.concat([df_xy.dtypes, nancount, nanperc], axis=1)
    nanmeta = pd.concat([nanmeta, zerocount], axis=1)
    nanmeta.columns = ['dtype', 'Nancount', 'DataPerc', 'Zerocount']
    stats = df_xy.describe().T
    meta_df = pd.concat([nanmeta, stats], axis=1)
    if index is None:
        df_index = df_xy
    else:
        df_index = df_xy.set_index(index)
    df_index = df_index.sort_index().index
    index_row = pd.DataFrame({'dtype': [str(df_index.dtype)], 'Nancount': 0, 'DataPerc': 100.0, 'Zerocount': 0,
                              'count': len(df_index), 'min': df_index[0], 'max': df_index[-1]},
                             index=[df_index.name])
    meta_df = pd.concat([meta_df, index_row])
    meta_df.to_csv(filename)


def length_check(df):
    start_ts = df.index[0]
    end_ts = df.index[-1]
    msg = f"{len(df)}\tentries;\t{start_ts} - {end_ts} (Total elapsed time: {str(end_ts-start_ts)[7:]})"
    return msg


def frequent(x):
    (value, counts) = np.unique(x, return_counts=True)
    if len(counts) > 0:
        return value[counts.argmax()]
    else:
        return np.nan


def plot_map(map_df, ax=None, cmap='Greens'):
    map_cols = np.array(map_df.columns, dtype=np.float)
    map_rows = np.array(map_df.index, dtype=np.float)
    extent_df = [map_cols[0], map_cols[-1], map_rows[-1], map_rows[0]]

    if ax is not None:
        plt.sca(ax)
    plt.imshow(map_df, cmap=cmap, extent=extent_df)


def plot_scenario(scen, ax):
    blue = "#0083ad"
    green = "#5e9582"

    agv2 = [-170/100, -10/100]
    agv3 = [(630 + 263)/100, (900 + 251)/100]
    ax.scatter(agv2[0], agv2[1], s=200, c=green, marker='*', zorder=30, label='AGV 2')
    ax.scatter(agv3[0], agv3[1], s=100, c=green, marker='s', zorder=30, label='AGV 3')

    # Plot adjacent room
    rect = patches.Rectangle((7.3, -2.0), 7.85, 12.1, linewidth=1, edgecolor='k', facecolor='#eeeeee')
    ax.add_patch(rect)

    msize = 8
    lwidth = 2.5

    if scen == "A":
        x_values = [(210 + 65)/100, (210 + 65 + 80)/100]
        y_values = [123/100, 123/100]
        ax.plot(x_values, y_values, linewidth=lwidth, c=blue, label='metal')

        y_values = np.arange(123, 123 + 150, 40)/100
        x_values = np.ones(len(y_values))*(210 + 65)/100
        ax.plot(x_values, y_values, linewidth=lwidth, c=blue, marker='^', markersize=msize, label='absorber')

        y_values = np.arange(123 + 150, 123 + 300, 40)/100
        x_values = np.ones(len(y_values))*(210 + 65)/100
        ax.plot(x_values, y_values, linewidth=lwidth, c=blue)

        x_values = np.arange(630 - 210, 630, 60)/100
        y_values = (np.ones(len(x_values))*(520+380+46))/100
        ax.plot(x_values, y_values, linewidth=lwidth, c=blue, marker='^', markersize=msize)
    elif scen == "B":
        x_values = [(210 + 65)/100, (210 + 65 + 80)/100]
        y_values = [123/100, 123/100]
        ax.plot(x_values, y_values, linewidth=lwidth, c=blue, label='metal')

        x_values = np.ones(7)*(210 + 65)/100
        y_values = (np.arange(len(x_values))*45+123)/100
        ax.plot(x_values, y_values, linewidth=lwidth, c=blue, marker='^', markersize=msize, label='absorber')
    else:
        raise ValueError(f"Unrecognized scenario '{scen}'")

    ax.legend(loc='lower right', ncol=2, framealpha=1.0)


def spatial_avg(df, pos_labels, tile_size, avg_method='mean'):
    x, y = pos_labels

    avg_df = df.copy()
    avg_df[x] = round(avg_df[x] / tile_size) * tile_size
    avg_df[y] = round(avg_df[y] / tile_size) * tile_size
    avg_df = avg_df.groupby([x, y]).aggregate(avg_method, numeric_only=True).reset_index()

    return avg_df
