# HW01 - Part 2 (Business Context Exploration)

## Prompt 1
"Wildcat's borrower data includes credit score, debt-to-income ratio, and annual income. What credit risk metrics do consumer lenders typically use to evaluate the relationship between these three borrower characteristics and a borrower's likelihood of becoming delinquent or defaulting, and which metrics would be most useful for Wildcat's portfolio risk management?"

### Response
Consumer lenders typically evaluate these three factors through PD scorecards (credit score is usually the strongest single predictor of 90+ day delinquency), DTI-based cutoffs like back-end DTI or payment-to-income, and income-based measures like residual income or income stability, then roll these into portfolio-level tools like expected loss (PD × LGD × EAD), vintage analysis, and roll rates to track cohort performance over time. For Wildcat specifically, the most useful starting point is a simple logistic regression or scorecard using score, DTI, and income to see which factor best predicts actual delinquency in your data, paired with risk-tier segmentation (score bands crossed with DTI bands) to map where risk concentrates in the current portfolio. Going forward, vintage/roll-rate tracking would be the most valuable ongoing metric since it catches deterioration early, before it shows up in aggregate default rates.

### Follow-up Question
Which of the three variables (credit score, DTI, or income) actually correlates most strongly with delinquency in Wildcat's own loan data, and are there any risk-tier or DTI-band combinations where default rates spike disproportionately?

## Prompt 2
Wildcat's portfolio is diversified across Auto, Personal, Home Improvement, Education, and Business loans. What information would a portfolio committee typically want to see in a quarterly review of a portfolio with this specific loan-purpose mix, and how might the committee's risk and performance priorities differ across these five segments?

### Response
A quarterly portfolio committee review would typically cover portfolio composition and growth by segment, delinquency/charge-off rates and vintage trends, yield and loss reserve coverage (ALLL/CECL) versus actual losses, and concentration limits by segment or risk tier. Priorities differ by segment: Auto (secured) focuses on LTV and recovery rates; Personal (unsecured) draws the closest scrutiny on delinquency and loss rates since there's no collateral cushion; Home Improvement watches draw/utilization and housing-market correlation; Education tracks cohort performance tied to repayment-start and career outcomes rather than immediate default; and Business emphasizes concentration risk (single-borrower/industry exposure) alongside default rate given its larger loan sizes. Net effect: unsecured and higher-variance segments (Personal, Business) get benchmarked tightly against loss reserves, while secured/long-duration segments (Auto, Home Improvement, Education) are evaluated more on collateral value and vintage trends.

### Follow-up Question
Within Wildcat's actual portfolio, how does delinquency rate, average loan size, and balance concentration break down across the five loan-purpose segments, and does any single segment (e.g., Business or Personal) represent an outsized share of total risk relative to its share of the portfolio?

## Prompt 3
Wildcat categorizes loans as Current, Paid Off, Delinquent, or Default. From a consumer-lending risk perspective, what is the distinction between delinquency and default, and how should Wildcat think about these four status categories when evaluating early warning signs, credit losses, and overall portfolio health?

### Response
Delinquency is a leading indicator (missed payments, still considered collectible, often bucketed by days past due), while default is a lagging, realized-loss event where the lender deems the loan uncollectible under original terms, triggering charge-off and reserves. Of Wildcat's four categories, Current is the healthy base to season new originations into, Delinquent is the key early-warning bucket to monitor via roll and cure rates, Default drives realized losses and recovery metrics, and Paid Off helps validate whether Current loans are performing as underwritten (and can flag prepayment risk). The most useful framing is to treat these as a flow rather than a snapshot, tracking transition rates between states (roll and cure rates) rather than static period-end percentages, since two portfolios with identical delinquency rates can have very different trajectories depending on whether that delinquency is curing or accelerating toward default.

### Follow-up Question
What are the actual roll rates and cure rates in Wildcat's data of loans that were ever Delinquent, what share cured back to Current versus rolled forward to Default, and does this vary meaningfully by loan-purpose segment or risk tier?

