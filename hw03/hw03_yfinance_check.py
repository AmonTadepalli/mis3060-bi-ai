"""Part 5C: pull Apple's recent quarterly revenue and net income from yfinance."""
import yfinance as yf

stmt = yf.Ticker("AAPL").quarterly_income_stmt

# Columns are quarter-end dates, newest first. Show the latest 4 quarters.
for col in stmt.columns[:4]:
    revenue = stmt.loc["Total Revenue", col]
    net_income = stmt.loc["Net Income", col]
    print(f"Quarter ended {col.date()} | Revenue: ${revenue/1e9:,.1f} billion | "
          f"Net Income: ${net_income/1e6:,.0f} million")
