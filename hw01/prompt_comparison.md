# Part 3 (Prompt Engineering Comparison)

## Strategy 1

### Prompt 
What are the most important metrics for measuring credit risk in a consumer loan portfolio?

### Response (First 150 words)
This is a knowledge question, so I'll just answer directly. Given the context (looks like it could tie into a Wildcat Capital project), here's the core picture:
Portfolio-level delinquency and default metrics
The backbone is the delinquency roll rate—the share of accounts moving from current to 30, 60, 90+ days past due each period. Charge-off rate (annualized net losses as a percentage of average receivables) and the related net charge-off vs. gross charge-off spread (which shows how much recovery activity is offsetting losses) round this out. Vintage analysis, tracking loss curves for loans originated in the same quarter or month, is what lets you separate a portfolio problem from an underwriting problem, since it isolates cohort performance from seasoning effects.
Borrower-level risk scores
FICO or VantageScore at origination and refreshed periodically show whether risk has drifted since underwriting. Debt-to-income ratio and loan-to-value ratio (for secured products) matter at both origination and on a rolling basis. 

### My thoughts 
Cowork recognized that this was a knowledge-based question, and because this was in the Wildcat Capital Project it had a baseline of what to refer to. Since my prompt did not specify any calculations, it did not refer to the excel sheet in the folder, but I do wish it did. Perhaps I should have specified that claude needed to refer to the excel file to answer this question, since I do find this response to be slightly generic.
