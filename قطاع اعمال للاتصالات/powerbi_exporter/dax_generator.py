"""
powerbi_exporter/dax_generator.py
==================================
Generates categorized DAX measures text files for Power BI import.
"""
from typing import Dict


def generate_dax_measures() -> Dict[str, str]:
    """
    Generates dictionary of categorized DAX measures text contents.
    Keys correspond to file names inside DAX/ directory.
    """
    core_measures = """// ===============================================================================
// CORE DEBT MEASURES (مقاييس المديونيات الأساسية)
// ===============================================================================

Total Debt = 
SUM(FactDebt[Debt_Amount])

Total Remaining = 
SUM(FactDebt[Remaining_Amount])

Total Documented Remaining = 
SUM(FactDebt[Documented_Remaining])

Average Debt = 
AVERAGE(FactDebt[Debt_Amount])

Average Remaining = 
AVERAGE(FactDebt[Remaining_Amount])

Customer Count = 
DISTINCTCOUNT(DimCustomer[Customer_ID])

Debt Count = 
COUNTROWS(FactDebt)

Average Debt per Customer = 
DIVIDE([Total Debt], [Customer Count], 0)
"""

    collection_measures = """// ===============================================================================
// COLLECTION MEASURES (مقاييس التحصيل والمطابقة)
// ===============================================================================

Total Collection = 
SUM(FactPayment[Payment_Amount])

Collection Rate = 
DIVIDE([Total Collection], [Total Debt], 0)

Paying Customers = 
CALCULATE(
    DISTINCTCOUNT(FactPayment[Customer_ID]),
    FactPayment[Payment_Amount] > 0
)

Customer Payment Rate = 
DIVIDE([Paying Customers], [Customer Count], 0)

Payment Transactions = 
COUNTROWS(FactPayment)

Average Payment = 
AVERAGE(FactPayment[Payment_Amount])

Median Payment = 
MEDIAN(FactPayment[Payment_Amount])

Maximum Payment = 
MAX(FactPayment[Payment_Amount])

Minimum Payment = 
MIN(FactPayment[Payment_Amount])

Payments per Paying Customer = 
DIVIDE([Payment Transactions], [Paying Customers], 0)

Total Documented Payments = 
SUM(FactDebt[Documented_Paid])

Documented Payment % = 
DIVIDE([Total Documented Payments], [Total Debt], 0)

Documented Remaining % = 
DIVIDE([Total Documented Remaining], [Total Debt], 0)

Collection Completion % = 
DIVIDE([Total Collection] + [Total Documented Payments], [Total Debt], 0)
"""

    collector_measures = """// ===============================================================================
// COLLECTOR MEASURES (مقاييس أداء المحصلين)
// ===============================================================================

Collector Debt = 
CALCULATE([Total Debt], ALLEXCEPT(DimCollector, DimCollector[Collector_Name]))

Collector Remaining = 
CALCULATE([Total Remaining], ALLEXCEPT(DimCollector, DimCollector[Collector_Name]))

Collector Payments = 
CALCULATE([Total Collection], ALLEXCEPT(DimCollector, DimCollector[Collector_Name]))

Collector Collection Rate = 
DIVIDE([Collector Payments], [Collector Debt], 0)

Collector Paying Customers = 
CALCULATE([Paying Customers], ALLEXCEPT(DimCollector, DimCollector[Collector_Name]))

Collector Payment Rate = 
DIVIDE([Collector Paying Customers], CALCULATE([Customer Count], ALLEXCEPT(DimCollector, DimCollector[Collector_Name])), 0)

Collector Average Payment = 
DIVIDE([Collector Payments], [Collector Paying Customers], 0)

Collector Rank = 
RANKX(
    ALL(DimCollector[Collector_Name]),
    [Collector Payments],
    ,
    DESC,
    Dense
)
"""

    supervisor_measures = """// ===============================================================================
// SUPERVISOR MEASURES (مقاييس أداء المشرفين)
// ===============================================================================

Supervisor Debt = 
CALCULATE([Total Debt], ALLEXCEPT(DimSupervisor, DimSupervisor[Supervisor_Name]))

Supervisor Remaining = 
CALCULATE([Total Remaining], ALLEXCEPT(DimSupervisor, DimSupervisor[Supervisor_Name]))

Supervisor Payments = 
CALCULATE([Total Collection], ALLEXCEPT(DimSupervisor, DimSupervisor[Supervisor_Name]))

Supervisor Collection Rate = 
DIVIDE([Supervisor Payments], [Supervisor Debt], 0)

Supervisor Paying Customers = 
CALCULATE([Paying Customers], ALLEXCEPT(DimSupervisor, DimSupervisor[Supervisor_Name]))

Supervisor Payment Rate = 
DIVIDE([Supervisor Paying Customers], CALCULATE([Customer Count], ALLEXCEPT(DimSupervisor, DimSupervisor[Supervisor_Name])), 0)

Supervisor Rank = 
RANKX(
    ALL(DimSupervisor[Supervisor_Name]),
    [Supervisor Payments],
    ,
    DESC,
    Dense
)
"""

    customer_measures = """// ===============================================================================
// CUSTOMER 360 & PROBABILITY MEASURES (تحليل العميل وتوقعات السداد)
// ===============================================================================

Customer Total Debt = 
SUM(Customer_Payment_History[Total_Debt])

Customer Total Payment = 
SUM(Customer_Payment_History[Total_Paid])

Customer Remaining = 
SUM(Customer_Payment_History[Total_Remaining])

Customer Payment % = 
AVERAGE(Customer_Payment_History[Payment_Percentage])

Customer Payment Count = 
SUM(Customer_Payment_History[Payment_Count])

First Available Payment = 
MIN(Customer_Payment_History[First_Payment_Date])

Last Available Payment = 
MAX(Customer_Payment_History[Last_Payment_Date])

Average Days Between Payments = 
AVERAGE(Customer_Payment_History[Average_Payment])

Days Since Last Payment = 
DATEDIFF(MAX(Customer_Payment_History[Last_Payment_Date]), TODAY(), DAY)

Payment Probability Score = 
AVERAGE(Customer_Payment_History[Payment_Probability_Score])
"""

    time_measures = """// ===============================================================================
// TIME INTELLIGENCE MEASURES (تحليل زمني ومؤشرات الفترات)
// ===============================================================================

Daily Collection = 
CALCULATE(
    [Total Collection],
    USERELATIONSHIP(DimDate[Date], FactPayment[Payment_Date])
)

MTD Collection = 
TOTALMTD([Total Collection], DimDate[Date])

Previous Month Collection = 
CALCULATE(
    [Total Collection],
    PREVIOUSMONTH(DimDate[Date])
)

Month-over-Month Change = 
DIVIDE([MTD Collection] - [Previous Month Collection], [Previous Month Collection], 0)

YTD Collection = 
TOTALYTD([Total Collection], DimDate[Date])

Previous Year Collection = 
CALCULATE(
    [Total Collection],
    SAMEPERIODLASTYEAR(DimDate[Date])
)

Collection Trend = 
DIVIDE([MTD Collection], [YTD Collection], 0)
"""

    return {
        'Core_Measures.txt': core_measures,
        'Collection_Measures.txt': collection_measures,
        'Collector_Measures.txt': collector_measures,
        'Supervisor_Measures.txt': supervisor_measures,
        'Customer_Measures.txt': customer_measures,
        'Time_Measures.txt': time_measures
    }
