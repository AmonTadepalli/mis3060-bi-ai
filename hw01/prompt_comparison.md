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
//

### Response
//

### My thoughts
//
