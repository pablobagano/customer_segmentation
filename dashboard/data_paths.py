import os

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

MARKETING_CAMPAIGN        = os.path.join(_DATA_DIR, "marketing_campaign.csv")
TREATED_DATA              = os.path.join(_DATA_DIR, "treated_data.csv")
SEGMENTED_DATA            = os.path.join(_DATA_DIR, "segmented_data.csv")
GROUPED_DATA_MEAN         = os.path.join(_DATA_DIR, "grouped_data_mean.csv")
GROUPED_DATA_STD          = os.path.join(_DATA_DIR, "grouped_data_std.csv")
PROPORTIONS_HIGHEST_SPENT = os.path.join(_DATA_DIR, "proportions_highest_spent.csv")