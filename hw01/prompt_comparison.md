# Part 3 (Prompt Engineering Comparison)

## Strategy 1

### Prompt 
Working from the "Wildcat" folder, What are the most important metrics for measuring credit risk in a consumer loan portfolio?

### Response (First 150 words)
Looking at the loan-level file in 02_Data/raw, this maps cleanly onto a real credit risk framework. Here's what I'd prioritize, roughly in order of how directly each answers "how risky is this portfolio":
Default and delinquency rates. The core metric. Your loan_status field already breaks loans into Current, Paid Off, Delinquent, and Default (currently 106 defaults and 248 delinquent out of 2,340 loans, about 4.5% and 10.6%). Track this both as count-based and dollar-weighted (defaults on larger loans hurt more than defaults on small ones).
Weighted average credit score and DTI. Your credit_score (500-850 range) and debt_to_income_ratio fields are the standard underwriting risk proxies. Look at the portfolio average, but more importantly segment default rate by credit score band (e.g., <620, 620-680, 680-740, 740+) and DTI band. This tells you which borrower tiers are actually driving losses.

### My thoughts 
I thought Claude Cowork provided a strong and well-grounded answer, using the actual Wildcat loan data rather than giving a generic credit-risk response. It identified the most important metrics and supported them with specific portfolio figures and relevant analysis. It also appropriately recognized limitations in the dataset, particularly the lack of recovery and detailed payment-history data. Overall, the response was thorough and useful, although slightly more technical and detailed than necessary for the question.

## Strategy 2

### Prompt
You are a senior credit risk strategist evaluating the performance of a consumer lending portfolio. Your audience is a team of credit risk managers responsible for monitoring portfolio health, identifying emerging risks, and making lending decisions. Working from the “Wildcat” folder and using the available loan-level credit data, what are the most important metrics for measuring credit risk in the consumer loan portfolio?

### Response
I pulled the actual loan-level data from your Wildcat folder (2,340 loans, $160.1M) and built a prioritized memo rather than a generic list. It's saved to your Drafts folder as Wildcat_Credit_Risk_Metrics_Memo.docx and also delivered above.

The headline finding from the data itself: 13.3% of balance is currently delinquent or in default. From there, the five metrics I'd actually put on a recurring dashboard, ranked by decision value, are:

Nonperforming balance % (delinquent + default) as the overall pulse check
Charge-off rate / expected loss, with the $14.3M delinquent bucket tracked as the loss pipeline
Weighted-average FICO and % of originations below 620, since FICO is by far the strongest predictor of bad loans in this book (correlation -0.20 vs. essentially zero for DTI)
Vintage bad-rate trend, since 2023-2025 originations are already running 17.6-18.4% bad rates versus 12.7-14.0% for 2018-2020, a real underwriting-drift signal
Concentration by loan purpose, since Business loans are 52% of dollar exposure despite being only 14% of loan count (HHI ≈ 3,400, highly concentrated)

The memo also flags two data gaps worth raising with the team: DTI isn't discriminating risk in this book (worth a sourcing/verification check) and 47 loans have no FICO on file. Full breakdowns and recommendations are in the document.

### My thoughts
The added context of a telling Claude that it was a senior credit risk strategist caused it to build an extremely detailed, comprehensive 11 page report. It used up a lot of tokens for a prompt that I thought did not require that much heavy lifting. Perhaps you must specify the format, and how you want the output to be released to avoid this. 

## Strategy 3

### Prompt
Working from the “Wildcat” folder and using the available loan-level credit data, what are the most important metrics for measuring credit risk in the consumer loan portfolio? Provide your response using the following structure:
1. Metric: [Name of metric]
Why it matters: [Brief explanation of why it is important for credit risk]
How to analyze it: [Brief explanation of how it could be evaluated using the available data]
2. Metric: [Name of metric]
Why it matters: [Brief explanation]
How to analyze it: [Brief explanation]
3. Metric: [Name of metric]
Why it matters: [Brief explanation]
How to analyze it: [Brief explanation]

### Response
Based on the loan-level data (wildcat_loans_clean.csv, 2,340 records), here are the three metrics that matter most for this portfolio:

Metric: Delinquency and default rate (by loan count and by dollar balance)
Why it matters: This is the front-line health check on the book. Wildcat currently sits at 10.6% of loans delinquent and 4.5% in default, and the dollar-weighted rates (8.9% and 4.4%) run lower than the count-weighted ones, meaning distressed loans skew toward smaller balances. Together, 13.3% of outstanding balance is nonperforming, the single number a risk committee should lead with.
How to analyze it: Segment the status field into current, delinquent, default, and paid-off, then compute both a loan-count share and a dollar-balance share for each. Since the extract only has a status label (no days-past-due field), the best available proxy for trend is comparing this snapshot period over period; pushing for 30/60/90+ DPD data would enable real roll-rate tracking.
Metric: Charge-off rate and expected loss
Why it matters: Defaulted balance is $7.0M (4.4% of the book), and applying standard loss-given-default assumptions (40-60%) puts estimated realized loss between $2.8M and $4.2M, or 1.8-2.6% of the portfolio.

### My thoughts
Claude’s response follows the requested format very well and provides specific, data-driven metrics rather than generic credit-risk concepts. It is detailed and demonstrates strong analysis of the dataset, although some claims—particularly the assumed LGD range and “strongest predictor” statement—go beyond what the prompt’s format example itself required. Specifying the output made the response a lot better for the level of complexity required in my opinion.
