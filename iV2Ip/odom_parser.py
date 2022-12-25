# This script to calculate distance, sum_obst, and Line of Sight


# Preliminary
from pathlib import Path
import numpy as np
import pandas as pd
from bagpy import bagreader
from datetime import datetime

import argparse

# For a better visualization check the sensor-enway-H.ipynb

# for input and output purposes
parser = argparse.ArgumentParser()
parser.add_argument("--input", "-i", type=str, help="Input file", metavar="INP")
parser.add_argument("--output", "-o", type=str, default=".", help="Output directory", metavar="OUT")

args = parser.parse_args()

# Constants
c = 3e8
n_fresnel = 1
bs_x, bs_y = 9, 9  # Position of base station
frequency = 3.79e9
wavelength = c/frequency

map_floor = 30

# Odometry
# Read
sensor_path = Path(args.input)
b = bagreader(str(sensor_path), tmp=True)   # read .bag file
out_path = Path(args.output)                # output folder

odom = b.message_by_topic("/global_odom") 
odom_df = pd.read_csv(odom)

odom_cols = odom_df.columns
odom_rename = {c: c.replace("pose.pose.", "").replace(".twist", "").replace(".", "_") for c in odom_cols}
odom_rename["Time"] = "timestamp"

odom_df = odom_df[list(odom_rename.keys())].rename(columns=odom_rename)

odom_df["timestamp"] = odom_df["timestamp"].apply(datetime.utcfromtimestamp)
odom_df.set_index("timestamp", inplace=True)
odom_df.index = odom_df.index.tz_localize("UTC").tz_convert("Europe/Berlin")


# Resample odom_df
# To match the sampling rate of the mobileinsight data.

sample = 0.04  # RSSI sampling-rate
sample = str("%.2f" % sample)
odom_df = odom_df.resample(sample + "S").bfill()


# Read the Static Map
elevation_map = b.message_by_topic("/navigation/enway_map/map_static_elevation")
elevation_df = pd.read_csv(elevation_map)

# Mapping
map_shape = elevation_df[["info.width", "info.height"]].to_numpy().flatten()
elev_series = elevation_df.T[0]
elev_map = np.reshape(np.array(elev_series[elev_series.index.str.contains("data_")], dtype=int), map_shape)
static_resolution = float("%.2f" % elevation_df["info.resolution"].to_numpy()[0])

# Remove the Floor of the Static Map
# In order to calculate the sum obstacle, the floor of the map is removed so only actual obstacle is in the map.
clean_map = np.where(elev_map >= map_floor, elev_map, 0)

# Calculate Distance between Base Station and Odometry Path


def euclidean_distance(x1, y1, x2, y2):
    x_diff = x1-x2
    y_diff = y1-y2
    return np.sqrt((x_diff*x_diff)+(y_diff*y_diff))


odom_df["distance_to_bs"] = euclidean_distance(odom_df["position_x"], odom_df["position_y"], bs_x, bs_y)

# Process the Static Data
# Creating Fresnel Zone

origin_x = elevation_df["info.origin.position.x"]
origin_y = elevation_df["info.origin.position.y"]

# Create the parameters for the fresnel zone

focal_distance = odom_df["distance_to_bs"] / 2
semiminor_axis = np.sqrt(odom_df["distance_to_bs"] * wavelength * n_fresnel) / 2
semimajor_axis = np.sqrt(focal_distance**2+semiminor_axis**2)
major_axis = 2*semimajor_axis

static_nx, static_ny = (map_shape[0], map_shape[1])
x_array = np.linspace(0, (static_nx-1)*static_resolution, static_nx) + origin_x
y_array = np.linspace(0, (static_ny-1)*static_resolution, static_ny) + origin_y

# Rely on numpy broadcasting
xv = x_array[:, np.newaxis]
yv = y_array[np.newaxis, :]


def sum_obstacles(df):
    dist_df = euclidean_distance(df["position_x"], df["position_y"], xv, yv)
    in_fresnel_mask = (sum_obstacles.dist_bs + dist_df) < df["major_axis"]
    los_obstacles = in_fresnel_mask * clean_map
    return np.sum(los_obstacles)


sum_obstacles.dist_bs = euclidean_distance(bs_x, bs_y, xv, yv)

odom_df = odom_df.assign(major_axis=major_axis)
odom_df["obstacles_sum"] = odom_df.apply(sum_obstacles, axis=1)
odom_df.drop(columns=["major_axis"], inplace=True)

# Create the Threshold of LoS. Here we choose the value 1000 as the Threshold.
# After creating the Heat Map for the static_mean,
# we see that the area between LoS and nLoS has a values of less than 1000
los_threshold = 1000
odom_df["line_of_sight"] = odom_df["obstacles_sum"] < los_threshold

odom_df.to_parquet("ros_df.parquet", compression="brotli")
