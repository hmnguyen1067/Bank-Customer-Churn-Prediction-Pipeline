import pandas as pd
from ydata_profiling import ProfileReport

data_path = "data/Customer-Churn-Records.csv"
save_path = "data/initial_report.html"

records = pd.read_csv(data_path)
records.drop(columns=["RowNumber", "CustomerId", "Surname"], inplace=True)

profile = ProfileReport(records, title="Initial Profiling Report", explorative=True)

profile.to_file(save_path)
