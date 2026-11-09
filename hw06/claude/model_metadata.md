# Model metadata (HW6 Part D, step 1)
Exported from DAX query view in `powerbi/hw06.pbix` on 2026-11-09 with the three INFO.VIEW queries from guide section 2.

## 1. Columns
```DAX
EVALUATE
SELECTCOLUMNS (
    FILTER ( INFO.VIEW.COLUMNS (), [DataCategory] <> "RowNumber" ),
    [Table], "Column", [Name], [DataType], "DAX formula", [Expression], [IsHidden]
)
ORDER BY [Table]
```
99 rows. The `DateTableTemplate_*` and `LocalDateTable_*` rows are hidden tables that Power BI's Auto date/time option creates; they are not part of the star schema.

| [Table] | [Column] | [DataType] | [DAX formula] | [IsHidden] |
|---|---|---|---|---|
| _Measures | Column1 | Text |  | false |
| DateTableTemplate_b50879b8-a09d-4fd7-b9a6-7a34995295aa | Date | Date |  | true |
| DateTableTemplate_b50879b8-a09d-4fd7-b9a6-7a34995295aa | Day | Integer | DAY([Date]) | true |
| DateTableTemplate_b50879b8-a09d-4fd7-b9a6-7a34995295aa | Quarter | Text | "Qtr " & [QuarterNo] | true |
| DateTableTemplate_b50879b8-a09d-4fd7-b9a6-7a34995295aa | QuarterNo | Integer | INT(([MonthNo] + 2) / 3) | true |
| DateTableTemplate_b50879b8-a09d-4fd7-b9a6-7a34995295aa | Month | Text | FORMAT([Date], "MMMM") | true |
| DateTableTemplate_b50879b8-a09d-4fd7-b9a6-7a34995295aa | MonthNo | Integer | MONTH([Date]) | true |
| DateTableTemplate_b50879b8-a09d-4fd7-b9a6-7a34995295aa | Year | Integer | YEAR([Date]) | true |
| dim_advisor | advisor_id | Integer |  | false |
| dim_advisor | certifications | Text |  | false |
| dim_advisor | aum_target_mm | Integer |  | false |
| dim_advisor | years_experience | Integer |  | false |
| dim_advisor | region | Text |  | false |
| dim_advisor | last_name | Text |  | false |
| dim_advisor | first_name | Text |  | false |
| dim_benchmark | name | Text |  | false |
| dim_benchmark | benchmark_id | Integer |  | false |
| dim_benchmark | ticker_proxy | Text |  | false |
| dim_benchmark | asset_class | Text |  | false |
| dim_client | age | Integer |  | false |
| dim_client | last_name | Text |  | false |
| dim_client | first_name | Text |  | false |
| dim_client | client_id | Integer |  | false |
| dim_client | zip_code | Text |  | false |
| dim_client | risk_profile | Text |  | false |
| dim_client | client_tier | Text |  | false |
| dim_client | primary_account_type | Text |  | false |
| dim_client | initial_aum | Number |  | false |
| dim_client | client_since | Date |  | false |
| dim_client | advisor_id | Integer |  | false |
| dim_client | is_active | True/False |  | false |
| dim_client | state | Text |  | false |
| dim_client | city | Text |  | false |
| dim_date | Quarter | Integer |  | false |
| dim_date | date_id | Integer |  | false |
| dim_date | Date | Date |  | false |
| dim_date | Year | Integer |  | false |
| dim_date | Month | Integer |  | false |
| dim_date | month_name | Text |  | false |
| dim_date | week_of_year | Integer |  | false |
| dim_date | day_of_week | Text |  | false |
| dim_date | is_month_end | Integer |  | false |
| dim_date | is_quarter_end | Integer |  | false |
| dim_date | is_year_end | Integer |  | false |
| dim_date | is_trading_day | Integer |  | false |
| dim_security | name | Text |  | false |
| dim_security | ticker | Text |  | false |
| dim_security | security_id | Integer |  | false |
| dim_security | expense_ratio_bps | Integer |  | false |
| dim_security | is_etf | True/False |  | false |
| dim_security | benchmark_id | Integer |  | false |
| dim_security | sector | Text |  | false |
| dim_security | asset_class | Text |  | false |
| fact_fees | aum_basis | Number |  | false |
| fact_fees | fee_type | Text |  | false |
| fact_fees | fee_date | Date |  | false |
| fact_fees | fee_id | Integer |  | false |
| fact_fees | client_id | Integer |  | false |
| fact_fees | advisor_id | Integer |  | false |
| fact_fees | amount | Number |  | false |
| fact_fees | bps_charged | Number |  | false |
| fact_portfolio_snapshot | cash_pct | Number |  | false |
| fact_portfolio_snapshot | benchmark_return_ytd | Number |  | false |
| fact_portfolio_snapshot | return_ytd | Number |  | false |
| fact_portfolio_snapshot | aum | Number |  | false |
| fact_portfolio_snapshot | Month | Integer |  | false |
| fact_portfolio_snapshot | Year | Integer |  | false |
| fact_portfolio_snapshot | snapshot_date | Date |  | false |
| fact_portfolio_snapshot | benchmark_id | Integer |  | false |
| fact_portfolio_snapshot | advisor_id | Integer |  | false |
| fact_portfolio_snapshot | client_id | Integer |  | false |
| fact_portfolio_snapshot | snapshot_id | Integer |  | false |
| fact_portfolio_snapshot | is_return_suspect | Integer |  | false |
| fact_portfolio_snapshot | account_type | Text |  | false |
| fact_portfolio_snapshot | active_alpha_ytd | Number |  | false |
| fact_transactions | shares | Number |  | false |
| fact_transactions | price | Number |  | false |
| fact_transactions | txn_date | Date |  | false |
| fact_transactions | advisor_id | Integer |  | false |
| fact_transactions | security_id | Integer |  | false |
| fact_transactions | amount | Number |  | false |
| fact_transactions | txn_type | Text |  | false |
| fact_transactions | client_id | Integer |  | false |
| fact_transactions | txn_id | Integer |  | false |
| fact_transactions | is_post_departure_txn | Integer |  | false |
| LocalDateTable_30b0d5f8-768e-4d2a-9562-888fa2f9b2e7 | QuarterNo | Integer | INT(([MonthNo] + 2) / 3) | true |
| LocalDateTable_30b0d5f8-768e-4d2a-9562-888fa2f9b2e7 | Date | Date |  | true |
| LocalDateTable_30b0d5f8-768e-4d2a-9562-888fa2f9b2e7 | Year | Integer | YEAR([Date]) | true |
| LocalDateTable_30b0d5f8-768e-4d2a-9562-888fa2f9b2e7 | MonthNo | Integer | MONTH([Date]) | true |
| LocalDateTable_30b0d5f8-768e-4d2a-9562-888fa2f9b2e7 | Month | Text | FORMAT([Date], "MMMM") | true |
| LocalDateTable_30b0d5f8-768e-4d2a-9562-888fa2f9b2e7 | Day | Integer | DAY([Date]) | true |
| LocalDateTable_30b0d5f8-768e-4d2a-9562-888fa2f9b2e7 | Quarter | Text | "Qtr " & [QuarterNo] | true |
| LocalDateTable_976ce71a-eea0-49bb-b089-dd421adaa4b8 | Year | Integer | YEAR([Date]) | true |
| LocalDateTable_976ce71a-eea0-49bb-b089-dd421adaa4b8 | MonthNo | Integer | MONTH([Date]) | true |
| LocalDateTable_976ce71a-eea0-49bb-b089-dd421adaa4b8 | Month | Text | FORMAT([Date], "MMMM") | true |
| LocalDateTable_976ce71a-eea0-49bb-b089-dd421adaa4b8 | QuarterNo | Integer | INT(([MonthNo] + 2) / 3) | true |
| LocalDateTable_976ce71a-eea0-49bb-b089-dd421adaa4b8 | Quarter | Text | "Qtr " & [QuarterNo] | true |
| LocalDateTable_976ce71a-eea0-49bb-b089-dd421adaa4b8 | Day | Integer | DAY([Date]) | true |
| LocalDateTable_976ce71a-eea0-49bb-b089-dd421adaa4b8 | Date | Date |  | true |

**Note for Claude:** column names are case-insensitive in DAX, so `dim_date[date]`, `dim_date[year]` and `dim_date[month]` resolve to `Date`, `Year` and `Month`. `fact_portfolio_snapshot` also has its own `Year` and `Month` columns. Those must not be used for time intelligence; always filter through `dim_date`.

## 2. Relationships
```DAX
EVALUATE INFO.VIEW.RELATIONSHIPS ()
```
14 rows: 11 fact-to-dimension relationships, the `dim_security → dim_benchmark` snowflake, and 2 auto-generated links to hidden `LocalDateTable`s. The `dim_date[date]` link to a `LocalDateTable` means Auto date/time is still on for `dim_date`, so it is **not** marked as a date table. Time intelligence still works because every fact joins `dim_date` on a Date-typed column, so a filter on `dim_date[date]` removes the other `dim_date` filters automatically (confirmed: `Ending AUM LY` for 2024 returns December 2023). Columns `[Model]`, `[RelyOnReferentialIntegrity]` (all false) and `[SecurityFilteringBehavior]` (all Single) are omitted, and GUID names are shortened to their first block.

| [ID] | [Name] | [Relationship] | [IsActive] | [CrossFilteringBehavior] | [FromTable] | [FromColumn] | [FromCardinality] | [ToTable] | [ToColumn] | [ToCardinality] | [State] |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2450 | AutoDetected_47d2c78f | 'fact_transactions'[advisor_id] *[<-]1 'dim_advisor'[advisor_id] | true | OneDirection | fact_transactions | advisor_id | Many | dim_advisor | advisor_id | One | Ready |
| 3424 | AutoDetected_080dc0c9 | 'fact_transactions'[client_id] *[<-]1 'dim_client'[client_id] | true | OneDirection | fact_transactions | client_id | Many | dim_client | client_id | One | Ready |
| 4453 | AutoDetected_2f815d05 | 'fact_transactions'[security_id] *[<-]1 'dim_security'[security_id] | true | OneDirection | fact_transactions | security_id | Many | dim_security | security_id | One | Ready |
| 4712 | 6deec966 | 'fact_transactions'[txn_date] *[<-]1 'dim_date'[date] | true | OneDirection | fact_transactions | txn_date | Many | dim_date | date | One | Ready |
| 2451 | AutoDetected_515f758c | 'fact_portfolio_snapshot'[advisor_id] *[<-]1 'dim_advisor'[advisor_id] | true | OneDirection | fact_portfolio_snapshot | advisor_id | Many | dim_advisor | advisor_id | One | Ready |
| 2639 | AutoDetected_27290db9 | 'fact_portfolio_snapshot'[benchmark_id] *[<-]1 'dim_benchmark'[benchmark_id] | true | OneDirection | fact_portfolio_snapshot | benchmark_id | Many | dim_benchmark | benchmark_id | One | Ready |
| 3425 | AutoDetected_8da07bbb | 'fact_portfolio_snapshot'[client_id] *[<-]1 'dim_client'[client_id] | true | OneDirection | fact_portfolio_snapshot | client_id | Many | dim_client | client_id | One | Ready |
| 4695 | aa81e5e4 | 'fact_portfolio_snapshot'[snapshot_date] *[<-]1 'dim_date'[date] | true | OneDirection | fact_portfolio_snapshot | snapshot_date | Many | dim_date | date | One | Ready |
| 2452 | AutoDetected_13cb45f8 | 'fact_fees'[advisor_id] *[<-]1 'dim_advisor'[advisor_id] | true | OneDirection | fact_fees | advisor_id | Many | dim_advisor | advisor_id | One | Ready |
| 3426 | AutoDetected_6b7ee019 | 'fact_fees'[client_id] *[<-]1 'dim_client'[client_id] | true | OneDirection | fact_fees | client_id | Many | dim_client | client_id | One | Ready |
| 4678 | fbd94a81 | 'fact_fees'[fee_date] *[<-]1 'dim_date'[date] | true | OneDirection | fact_fees | fee_date | Many | dim_date | date | One | Ready |
| 2662 | 371030ed | 'dim_client'[client_since] *[<-]1 'LocalDateTable_976ce71a'[Date] | true | OneDirection | dim_client | client_since | Many | LocalDateTable_976ce71a | date | One | Ready |
| 3498 | 4ef23535 | 'dim_date'[date] *[<-]1 'LocalDateTable_30b0d5f8'[Date] | true | OneDirection | dim_date | date | Many | LocalDateTable_30b0d5f8 | date | One | Ready |
| 4454 | AutoDetected_031cb484 | 'dim_security'[benchmark_id] *[<-]1 'dim_benchmark'[benchmark_id] | true | OneDirection | dim_security | benchmark_id | Many | dim_benchmark | benchmark_id | One | Ready |

## 3. Measures
```DAX
EVALUATE
SELECTCOLUMNS (
    INFO.VIEW.MEASURES (),
    [Table], "Measure", [Name], "DAX formula", [Expression], [FormatString], [State]
)
```
Run after the measure library was added (16 rows, all Valid; format strings were set afterwards in Model view). For the Part D prompt, measure 9 and the measures built on it (10) were removed from this list, so Claude had to write it from scratch.

| [Table] | [Measure] | [DAX formula] | [FormatString] | [State] |
|---|---|---|---|---|
| _Measures | Total Fees | `SUM ( fact_fees[amount] )` | | Valid |
| _Measures | Net Flows | `CALCULATE ( SUM ( fact_transactions[amount] ), fact_transactions[txn_type] = "Deposit" ) - CALCULATE ( SUM ( fact_transactions[amount] ), fact_transactions[txn_type] = "Withdrawal" )` | | Valid |
| _Measures | AUM (naive SUM) | `SUM ( fact_portfolio_snapshot[aum] )` (with a "WRONG ON PURPOSE" comment) | | Valid |
| _Measures | Ending AUM | `CALCULATE ( SUM ( fact_portfolio_snapshot[aum] ), LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) ) )` | | Valid |
| _Measures | Ending Clients | `CALCULATE ( DISTINCTCOUNT ( fact_portfolio_snapshot[client_id] ), LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) ) )` | | Valid |
| _Measures | Avg AUM per Client | `DIVIDE ( [Ending AUM], [Ending Clients] )` | | Valid |
| _Measures | Ending AUM LY | `CALCULATE ( [Ending AUM], SAMEPERIODLASTYEAR ( dim_date[date] ) )` | | Valid |
| _Measures | AUM YoY % | `DIVIDE ( [Ending AUM] - [Ending AUM LY], [Ending AUM LY] )` | | Valid |
| _Measures | Ending AUM PM | `CALCULATE ( [Ending AUM], DATEADD ( dim_date[date], -1, MONTH ) )` | | Valid |
| _Measures | AUM MoM % | `DIVIDE ( [Ending AUM] - [Ending AUM PM], [Ending AUM PM] )` | | Valid |
| _Measures | Avg Monthly AUM | `DIVIDE ( SUM ( fact_portfolio_snapshot[aum] ), DISTINCTCOUNT ( fact_portfolio_snapshot[snapshot_date] ) )` | | Valid |
| _Measures | Fee Yield (bps) | `DIVIDE ( [Total Fees] * 12 * 10000, SUM ( fact_portfolio_snapshot[aum] ) )` | | Valid |
| _Measures | Organic Growth Rate | `DIVIDE ( [Net Flows], [Ending AUM LY] )` | | Valid |
| _Measures | AUM-Weighted Alpha | *(see `powerbi/measures.md`, measure 9)* | | Valid |
| _Measures | Alpha Signal | *(see `powerbi/measures.md`, measure 10)* | | Valid |
| _Measures | Top 10 Client Share | *(see `powerbi/measures.md`, measure 11)* | | Valid |
