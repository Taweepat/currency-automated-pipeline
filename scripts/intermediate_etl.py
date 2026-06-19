import os
import sqlite3
import pandas as pd
import requests
import logging
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "currency_warehouse.db")
API_URL = "https://v6.exchangerate-api.com/v6/ca5c46dfb375fc89c24314ab/latest/USD"

def run_etl():
    logging.info("Starting ETL process...")

    response = requests.get(API_URL, timeout=10)

    try:
        if response.status_code == 200:
            raw_data = response.json()
            logging.info("Extracted data successfully.")
        else:
            logging.error(f"Error: {response.status_code}")
            return
    except requests.RequestException as e:
        logging.error(f"Error fetching API data: {e}")
        return

    logging.info("Transforming data...")

    try:
        rates_dict = raw_data.get("conversion_rates")
        df_current = pd.DataFrame(list(rates_dict.items()), columns=["currency", "rate"])
        df_current["fetch_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        target_currencies = ["THB", "JPY", "EUR", "GBP", "SGD"]
        df_current = df_current[df_current["currency"].isin(target_currencies)]

        with sqlite3.connect(DB_PATH) as conn:
            existing_tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='fact_exchange_rates'"
            ).fetchone()
            if existing_tables:
                existing_cols = [row[1] for row in conn.execute("PRAGMA table_info(fact_exchange_rates)").fetchall()]
                required_cols = {"currency", "rate", "fetch_time", "pct_from_avg", "market_signal"}
                if not required_cols.issubset(set(existing_cols)):
                    conn.execute("DROP TABLE fact_exchange_rates")
                    conn.execute(
                        "CREATE TABLE fact_exchange_rates "
                        "(currency TEXT, rate REAL, fetch_time TEXT, pct_from_avg REAL, market_signal TEXT)"
                    )
            else:
                conn.execute(
                    "CREATE TABLE fact_exchange_rates "
                    "(currency TEXT, rate REAL, fetch_time TEXT, pct_from_avg REAL, market_signal TEXT)"
                )
            try:
                df_historical = pd.read_sql_query(
                    """
                    WITH ranked AS (
                        SELECT currency, rate, fetch_time,
                               ROW_NUMBER() OVER (PARTITION BY currency ORDER BY fetch_time DESC) AS rn
                        FROM fact_exchange_rates
                    )
                    SELECT currency, rate AS avg_rate
                    FROM ranked
                    WHERE rn = 2
                    """,
                    conn,
                )

                df_merged = pd.merge(df_current, df_historical, on="currency", how="left")

                df_merged["avg_rate"] = df_merged["avg_rate"].fillna(df_merged["rate"])

                # Avoid division by zero
                df_merged["avg_rate"] = df_merged["avg_rate"].replace(0, float("nan"))

                df_merged["pct_from_avg"] = (
                    (df_merged["rate"] - df_merged["avg_rate"]) / df_merged["avg_rate"]
                ) * 100

                def generate_signal(row):
                    if pd.isna(row["pct_from_avg"]):
                        return "No Signal"
                    elif row["pct_from_avg"] > 0.05:
                        return "Weakening USD"
                    elif row["pct_from_avg"] < -0.05:
                        return "Strengthening USD"
                    else:
                        return "Stable USD"

                df_merged["market_signal"] = df_merged.apply(generate_signal, axis=1)

                df_current = df_current.assign(
                    pct_from_avg=df_merged["pct_from_avg"].values,
                    market_signal=df_merged["market_signal"].values,
                )

                df_current.to_sql("fact_exchange_rates", conn, if_exists="append", index=False)

            except Exception as db_error:
                logging.error(f"DB error during transform: {type(db_error).__name__}: {db_error}")
                df_current["market_signal"] = "No historical data"
                df_current["pct_from_avg"] = 0.0

        logging.info("Transformed data:")
        print(df_current)

    except Exception as transform_error:
                logging.error(f"Error transformation: {transform_error}")
                return

    try:
        with sqlite3.connect(DB_PATH) as conn:
            df_all_history = pd.read_sql_query("SELECT fetch_time, rate , currency FROM fact_exchange_rates ", conn)

        if len(df_all_history) > 0:
            plt.figure(figsize=(10, 5))
            sns.lineplot(data=df_all_history, x="fetch_time", y="rate", hue="currency" , marker= "o")
            plt.title("Currency Exchange Rates Over Time")
            plt.xticks(rotation=45)
            plt.tight_layout()

            output_dir = os.path.join(os.path.dirname(__file__), "..", "outputs")
            os.makedirs(output_dir, exist_ok=True)
            plt.savefig(os.path.join(output_dir, "currency_exchange_rates.png"))
            plt.close()
            logging.info("Visualization saved successfully.")
        else:
            logging.info("No historical data available for visualization.")
    except Exception as db_error:
        logging.error(f"Load error unsuccessful: {db_error}")
if __name__ == "__main__":
    run_etl()