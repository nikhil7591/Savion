def get_investment_advice(balance, income, expense):
    if balance < 0:
        return "Your balance is negative. Reduce expenses or increase income. Consider emergency fund."
    elif expense > income * 0.8:
        return "High spending detected. Try to save at least 20% of your income."
    else:
        return "Good financial health. Consider investing in SIPs or mutual funds."